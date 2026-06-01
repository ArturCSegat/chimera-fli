from __future__ import annotations

import ctypes
import ctypes.util
import os
from enum import IntEnum
from typing import Optional


class FliError(RuntimeError):
    def __init__(self, func: str, code: int):
        super().__init__(f"FLI SDK call failed: {func} returned {code} (errno {-code})")
        self.func = func
        self.code = code


# Domain / device-type constants (from libfli.h).
class FliDomain(IntEnum):
    """Interface constants — combined with FliDeviceType via bitwise OR."""
    PARALLEL_PORT = 0x01
    USB           = 0x02
    SERIAL        = 0x03
    INET          = 0x04


class FliDeviceType(IntEnum):
    """Device type constants (FLIDEVICE_* in libfli.h) — combined with FliDomain via bitwise OR."""
    CAMERA           = 0x100
    FILTERWHEEL      = 0x200
    FOCUSER          = 0x300


# Invalid / uninitialized handle value per the SDK spec.
FLI_INVALID_DEVICE: int = -1


def _resolve_sdk_library_path(explicit_path: Optional[str] = None) -> str:
    if explicit_path:
        return explicit_path

    env_path = os.getenv("FLI_SDK_PATH") or os.getenv("FLI_LIB_PATH")
    if env_path:
        return env_path

    for p in ("/usr/local/lib/libfli.so", "/usr/lib64/libfli.so", "/usr/lib/libfli.so"):
        if os.path.exists(p):
            return p

    found = ctypes.util.find_library("fli")
    if found:
        return found

    return "/usr/local/lib/libfli.so"


class FliSdk:
    """ctypes-only wrapper around libfli.

    Only the functions used by FliDriver are bound here.
    No device-level state — no stored handles, no position tracking.
    All functions raise FliError on non-zero return codes.
    """

    def __init__(self, library_path: Optional[str] = None):
        lib_path = _resolve_sdk_library_path(library_path)
        self._lib = ctypes.CDLL(lib_path)
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        # All FLI SDK functions return long (0 = success, non-zero = -errno).
        _long = ctypes.c_long
        _plong = ctypes.POINTER(ctypes.c_long)
        _str = ctypes.c_char_p
        _sz = ctypes.c_size_t

        self._lib.FLIGetLibVersion.restype = _long
        self._lib.FLIGetLibVersion.argtypes = [_str, _sz]

        self._lib.FLICreateList.restype = _long
        self._lib.FLICreateList.argtypes = [_long]

        self._lib.FLIDeleteList.restype = _long
        self._lib.FLIDeleteList.argtypes = []

        self._lib.FLIListFirst.restype = _long
        self._lib.FLIListFirst.argtypes = [_plong, _str, _sz, _str, _sz]

        self._lib.FLIListNext.restype = _long
        self._lib.FLIListNext.argtypes = [_plong, _str, _sz, _str, _sz]

        self._lib.FLIOpen.restype = _long
        self._lib.FLIOpen.argtypes = [_plong, _str, _long]

        self._lib.FLIClose.restype = _long
        self._lib.FLIClose.argtypes = [_long]

        self._lib.FLIGetModel.restype = _long
        self._lib.FLIGetModel.argtypes = [_long, _str, _sz]

        self._lib.FLIGetFWRevision.restype = _long
        self._lib.FLIGetFWRevision.argtypes = [_long, _plong]

        self._lib.FLIGetHWRevision.restype = _long
        self._lib.FLIGetHWRevision.argtypes = [_long, _plong]

        self._lib.FLIGetFilterCount.restype = _long
        self._lib.FLIGetFilterCount.argtypes = [_long, _plong]

        self._lib.FLIGetFilterPos.restype = _long
        self._lib.FLIGetFilterPos.argtypes = [_long, _plong]

        self._lib.FLISetFilterPos.restype = _long
        self._lib.FLISetFilterPos.argtypes = [_long, _long]

        self._lib.FLIGetStepsRemaining.restype = _long
        self._lib.FLIGetStepsRemaining.argtypes = [_long, _plong]

        self._lib.FLILockDevice.restype = _long
        self._lib.FLILockDevice.argtypes = [_long]

        self._lib.FLIUnlockDevice.restype = _long
        self._lib.FLIUnlockDevice.argtypes = [_long]

    @staticmethod
    def _check(code: int, func: str) -> None:
        if int(code) != 0:
            raise FliError(func, int(code))

    # ------------------------------------------------------------------
    # Library
    # ------------------------------------------------------------------

    def get_lib_version(self) -> str:
        buf = ctypes.create_string_buffer(64)
        self._check(self._lib.FLIGetLibVersion(buf, ctypes.c_size_t(len(buf))), "FLIGetLibVersion")
        return buf.value.decode("utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Enumeration
    # ------------------------------------------------------------------

    def list_devices(self, domain: int) -> list[tuple[str, str]]:
        """Return [(filename, model_name), ...] for all devices matching domain."""
        self._check(self._lib.FLICreateList(ctypes.c_long(int(domain))), "FLICreateList")

        devices: list[tuple[str, str]] = []
        fn_buf       = ctypes.create_string_buffer(256)
        name_buf     = ctypes.create_string_buffer(256)
        found_domain = ctypes.c_long(0)

        try:
            rc = self._lib.FLIListFirst(
                ctypes.byref(found_domain),
                fn_buf,   ctypes.c_size_t(len(fn_buf)),
                name_buf, ctypes.c_size_t(len(name_buf)),
            )
            while rc == 0:
                devices.append((
                    fn_buf.value.decode("utf-8", errors="replace"),
                    name_buf.value.decode("utf-8", errors="replace"),
                ))
                rc = self._lib.FLIListNext(
                    ctypes.byref(found_domain),
                    fn_buf,   ctypes.c_size_t(len(fn_buf)),
                    name_buf, ctypes.c_size_t(len(name_buf)),
                )
        finally:
            self._lib.FLIDeleteList()

        return devices

    def open(self, filename: str, domain: int) -> int:
        """Open a device; returns its flidev_t handle."""
        dev = ctypes.c_long(FLI_INVALID_DEVICE)
        self._check(
            self._lib.FLIOpen(
                ctypes.byref(dev),
                filename.encode("utf-8"),
                ctypes.c_long(int(domain)),
            ),
            "FLIOpen",
        )
        return int(dev.value)

    def close(self, handle: int) -> None:
        self._check(self._lib.FLIClose(ctypes.c_long(int(handle))), "FLIClose")

    def get_model(self, handle: int) -> str:
        buf = ctypes.create_string_buffer(128)
        self._check(
            self._lib.FLIGetModel(ctypes.c_long(int(handle)), buf, ctypes.c_size_t(len(buf))),
            "FLIGetModel",
        )
        return buf.value.decode("utf-8", errors="replace")

    def get_fw_revision(self, handle: int) -> int:
        rev = ctypes.c_long()
        self._check(
            self._lib.FLIGetFWRevision(ctypes.c_long(int(handle)), ctypes.byref(rev)),
            "FLIGetFWRevision",
        )
        return int(rev.value)

    def get_hw_revision(self, handle: int) -> int:
        rev = ctypes.c_long()
        self._check(
            self._lib.FLIGetHWRevision(ctypes.c_long(int(handle)), ctypes.byref(rev)),
            "FLIGetHWRevision",
        )
        return int(rev.value)

    def get_filter_count(self, handle: int) -> int:
        n = ctypes.c_long()
        self._check(
            self._lib.FLIGetFilterCount(ctypes.c_long(int(handle)), ctypes.byref(n)),
            "FLIGetFilterCount",
        )
        return int(n.value)

    def get_filter_pos(self, handle: int) -> int:
        pos = ctypes.c_long()
        self._check(
            self._lib.FLIGetFilterPos(ctypes.c_long(int(handle)), ctypes.byref(pos)),
            "FLIGetFilterPos",
        )
        return int(pos.value)

    def set_filter_pos(self, handle: int, position: int) -> None:
        self._check(
            self._lib.FLISetFilterPos(ctypes.c_long(int(handle)), ctypes.c_long(int(position))),
            "FLISetFilterPos",
        )

    def get_steps_remaining(self, handle: int) -> int:
        steps = ctypes.c_long()
        self._check(
            self._lib.FLIGetStepsRemaining(ctypes.c_long(int(handle)), ctypes.byref(steps)),
            "FLIGetStepsRemaining",
        )
        return int(steps.value)

    def lock_device(self, handle: int) -> None:
        self._check(self._lib.FLILockDevice(ctypes.c_long(int(handle))), "FLILockDevice")

    def unlock_device(self, handle: int) -> None:
        self._check(self._lib.FLIUnlockDevice(ctypes.c_long(int(handle))), "FLIUnlockDevice")
