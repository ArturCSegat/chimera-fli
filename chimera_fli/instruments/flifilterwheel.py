from __future__ import annotations

from chimera.core.lock import lock
from chimera.instruments.filterwheel import FilterWheelBase
from chimera.interfaces.filterwheel import InvalidFilterPositionException

from flidriver import FliDriver


class FLIFilterWheel(FilterWheelBase):
    """FLI USB filter wheel as a Chimera instrument."""

    __config__ = {
        "device": None,           
        "filter_wheel_model": None,
        "filters": None,
        "sdk_library_path": None,
        "fake": False,
        "move_timeout_s": 30,
    }

    def __init__(self):
        super().__init__()
        self.drv: FliDriver | None = None

    @lock
    def __start__(self):
        self.log.info("Starting FLI filter wheel (fake=%s)", self["fake"])

        if self['filters'] is None or self["filter_wheel_model"] is None or self["sdk_library_path"] is None:
            raise RuntimeError(
                "Missing required configuration: 'filters', 'filter_wheel_model', and 'sdk_library_path' must all be set"
            )

        self.drv = FliDriver(
            self.log,
            device_filename=self["device"] or None,
            sdk_library_path=self["sdk_library_path"] or None,
            move_timeout_s=float(self["move_timeout_s"]),
            use_mock_sdk=bool(self["fake"]),
        )
        self.drv.open()

        configured = len(self.get_filters())
        hardware   = self.drv.state.filter_count
        if configured != hardware:
            self.log.warning(
                "Config lists %d filter name(s) but wheel reports %d position(s); "
                "update 'filters' in chimera.config",
                configured,
                hardware,
            )

    @lock
    def __stop__(self):
        self.log.info("Stopping FLI filter wheel")
        if self.drv is not None:
            self.drv.close()

    def get_filter(self) -> str:
        if self.drv is None:
            raise RuntimeError("Filter wheel not started")

        pos = self.drv.get_position()
        return self._get_filter_name(pos)

    @lock
    def set_filter(self, filter) -> None:
        filter_name = str(filter)
        if filter_name not in self.get_filters():
            raise InvalidFilterPositionException(f"Invalid filter {filter!r}.")

        old = self.get_filter()
        pos = self._get_filter_position(filter_name)

        if self.drv is None:
            raise RuntimeError("Filter wheel not started")

        try:
            self.drv.set_position(pos)
        except Exception as e:
            raise InvalidFilterPositionException(
                f"Failed to move filter wheel to {filter_name!r}: {e}"
            ) from e

        self.filter_change(filter_name, old)
