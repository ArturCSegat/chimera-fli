from __future__ import annotations

from dataclasses import dataclass

from flisdk import FliError, FLI_INVALID_DEVICE


@dataclass
class _MockDevice:
    filename: str
    model: str
    handle: int
    filter_count: int = 7
    current_position: int = 0
    fw_revision: int = 0x10
    hw_revision: int = 0x01
    steps_remaining: int = 0


class FliSdkMock:
    """Mock implementation of FliSdk for local testing.

    Every method prints when called. State mutations are consistent so
    reads after writes return the expected values.

    Drop-in replacement for FliSdk in FliDriver (use_mock_sdk=True).
    """

    def __init__(self, *, filter_count: int = 7):
        self._filter_count = int(filter_count)
        self._next_handle = 1
        self._devices: dict[int, _MockDevice] = {}
        print(f"[FliSdkMock] init (filter_count={self._filter_count})")

    def get_lib_version(self) -> str:
        print("[FliSdkMock] get_lib_version")
        return "FLI SDK mock v1.40"

    def list_devices(self, domain: int) -> list[tuple[str, str]]:
        print(f"[FliSdkMock] list_devices(domain={domain:#x})")
        return [("/dev/fliusb0", "FLI CFW-7-7 USB Filter Wheel")]

    def open(self, filename: str, domain: int) -> int:
        print(f"[FliSdkMock] open(filename={filename!r}, domain={domain:#x})")
        handle = self._next_handle
        self._next_handle += 1
        self._devices[handle] = _MockDevice(
            filename=filename,
            model="FLI CFW-7-7 USB Filter Wheel",
            handle=handle,
            filter_count=self._filter_count,
        )
        return handle

    def close(self, handle: int) -> None:
        print(f"[FliSdkMock] close(handle={handle})")
        self._devices.pop(int(handle), None)

    def get_model(self, handle: int) -> str:
        print(f"[FliSdkMock] get_model(handle={handle})")
        return self._devices[int(handle)].model

    def get_fw_revision(self, handle: int) -> int:
        print(f"[FliSdkMock] get_fw_revision(handle={handle})")
        return self._devices[int(handle)].fw_revision

    def get_hw_revision(self, handle: int) -> int:
        print(f"[FliSdkMock] get_hw_revision(handle={handle})")
        return self._devices[int(handle)].hw_revision

    def get_filter_count(self, handle: int) -> int:
        print(f"[FliSdkMock] get_filter_count(handle={handle})")
        return self._devices[int(handle)].filter_count

    def get_filter_pos(self, handle: int) -> int:
        print(f"[FliSdkMock] get_filter_pos(handle={handle})")
        return self._devices[int(handle)].current_position

    def set_filter_pos(self, handle: int, position: int) -> None:
        print(f"[FliSdkMock] set_filter_pos(handle={handle}, position={position})")
        dev = self._devices[int(handle)]
        if not (0 <= int(position) < dev.filter_count):
            raise FliError("FLISetFilterPos", -1)
        dev.current_position = int(position)
        dev.steps_remaining = 0

    def get_steps_remaining(self, handle: int) -> int:
        print(f"[FliSdkMock] get_steps_remaining(handle={handle})")
        return self._devices[int(handle)].steps_remaining

    def lock_device(self, handle: int) -> None:
        print(f"[FliSdkMock] lock_device(handle={handle})")

    def unlock_device(self, handle: int) -> None:
        print(f"[FliSdkMock] unlock_device(handle={handle})")
