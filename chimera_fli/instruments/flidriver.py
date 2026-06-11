from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from flisdk import FliDeviceType, FliDomain, FliError, FliSdk, FLI_INVALID_DEVICE
from flisdk_mock import FliSdkMock

_EPIPE = -32  # errno 32: USB pipe broken — device disconnected mid-transfer

@dataclass
class FliWheelState:
    device_filename: Optional[str] = None
    handle: int = FLI_INVALID_DEVICE
    model: str = ""
    fw_revision: int = 0
    hw_revision: int = 0
    filter_count: int = 0
    current_position: int = 0
    reconnect_attempts: int = 0


class FliDriver:
    """Manages device lifecycle, move polling and reconnect logic"""

    _POLL_INTERVAL_S: float = 0.05
    _DEFAULT_DOMAIN: int = int(FliDomain.USB) | int(FliDeviceType.FILTERWHEEL)

    def __init__(
        self,
        chimera_logger: logging.Logger,
        *,
        device_filename: Optional[str] = None,
        sdk_library_path: Optional[str] = None,
        move_timeout_s: float = 30.0,
        use_mock_sdk: bool = False,
    ):
        self.log = chimera_logger
        self._device_filename = device_filename
        self._sdk_library_path = sdk_library_path
        self._move_timeout_s = float(move_timeout_s)
        self._use_mock_sdk = bool(use_mock_sdk)

        self._sdk: FliSdk | FliSdkMock
        self.state = FliWheelState()

    def open(self) -> None:
        if self._use_mock_sdk:
            self._sdk = FliSdkMock()
        else:
            self._sdk = FliSdk(self._sdk_library_path)

        lib_ver = self._sdk.get_lib_version()
        self.log.info("FLI SDK version: %s", lib_ver)

        filename = self._device_filename or self._autodiscover()

        self.state.handle = self._sdk.open(filename, self._DEFAULT_DOMAIN)
        self.state.device_filename = filename

        self.state.model        = self._sdk.get_model(self.state.handle)
        self.state.fw_revision  = self._sdk.get_fw_revision(self.state.handle)
        self.state.hw_revision  = self._sdk.get_hw_revision(self.state.handle)
        self.state.filter_count = self._sdk.get_filter_count(self.state.handle)
        self.state.current_position = self._sdk.get_filter_pos(self.state.handle)

        self.log.info(
            "FLI filter wheel opened: model=%r filename=%r fw=%d hw=%d positions=%d",
            self.state.model,
            self.state.device_filename,
            self.state.fw_revision,
            self.state.hw_revision,
            self.state.filter_count,
        )

    _MAX_RECONNECTS = 3
    _RECONNECT_DELAY_S = (1.0, 5.0, 10.0)

    def _reconnect(self) -> None:
        """Close the stale handle and reopen"""
        if self.state.reconnect_attempts >= self._MAX_RECONNECTS:
            raise RuntimeError(
                f"FLI device failed to reconnect after {self._MAX_RECONNECTS} attempts"
            )
        delay = self._RECONNECT_DELAY_S[self.state.reconnect_attempts]
        self.state.reconnect_attempts += 1
        self.log.warning(
            "FLI USB disconnected (EPIPE) — reconnect attempt %d/%d in %.0f s…",
            self.state.reconnect_attempts,
            self._MAX_RECONNECTS,
            delay,
        )
        try:
            self._sdk.close(self.state.handle)
        except Exception:
            pass
        finally:
            self.state.handle = FLI_INVALID_DEVICE
        time.sleep(delay)
        self.state.handle = self._sdk.open(self.state.device_filename, self._DEFAULT_DOMAIN)
        self.state.reconnect_attempts = 0
        self.log.info("FLI device reconnected")

    def _try_with_reconnect(self, fn):
        """Call fn(); on EPIPE reconnect and retry up to _MAX_RECONNECTS times."""
        while True:
            try:
                return fn()
            except FliError as e:
                if e.code != _EPIPE:
                    raise
                self._reconnect()

    def close(self) -> None:
        if self.state.handle == FLI_INVALID_DEVICE:
            return
        try:
            self._sdk.close(self.state.handle)
        finally:
            self.state.handle = FLI_INVALID_DEVICE

    def get_position(self) -> int:
        """Return current wheel position (0-indexed)."""
        if self.state.handle == FLI_INVALID_DEVICE:
            raise RuntimeError("Filter wheel not open")
        self.state.current_position = self._try_with_reconnect(
            lambda: self._sdk.get_filter_pos(self.state.handle)
        )
        return self.state.current_position

    def set_position(self, position: int) -> None:
        """Move to position (0-indexed) and block until the motor stops."""
        if self.state.handle == FLI_INVALID_DEVICE:
            raise RuntimeError("Filter wheel not open")
        if not (0 <= int(position) < self.state.filter_count):
            raise ValueError(
                f"Position {position} out of range (0–{self.state.filter_count - 1})"
            )

        self.log.info(
            "Moving FLI filter wheel: %d → %d",
            self.state.current_position,
            position,
        )

        self._try_with_reconnect(lambda: self._sdk.lock_device(self.state.handle))
        try:
            self._try_with_reconnect(
                lambda: self._sdk.set_filter_pos(self.state.handle, int(position))
            )
            self._wait_for_move()
            self.state.current_position = self._try_with_reconnect(
                lambda: self._sdk.get_filter_pos(self.state.handle)
            )
        finally:
            try:
                self._sdk.unlock_device(self.state.handle)
            except Exception:
                pass

        self.log.info("FLI filter wheel at position %d", self.state.current_position)

    def _wait_for_move(self) -> None:
        deadline = time.monotonic() + self._move_timeout_s
        while time.monotonic() < deadline:
            if self._try_with_reconnect(
                lambda: self._sdk.get_steps_remaining(self.state.handle)
            ) == 0:
                return
            time.sleep(self._POLL_INTERVAL_S)
        raise RuntimeError(
            f"FLI filter wheel move timed out after {self._move_timeout_s}s"
        )

    def _autodiscover(self) -> str:
        devices = self._sdk.list_devices(self._DEFAULT_DOMAIN)
        if not devices:
            raise RuntimeError(
                """No FLI filter wheel found on USB.\n
                Verify its plugged in and the fliusb driver is loaded"""
            )
        filename, model = devices[0]
        self.log.info("FLI auto-discovered: %r (%s)", filename, model)
        return filename
