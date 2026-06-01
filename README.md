# chimera-fli

[FLI](https://www.flicamera.com/) USB filter wheel plugin for [Chimera](https://github.com/astroufsc/chimera).

## Requirements

- `libfli.so` installed on the system (FLI SDK v1.40+) [Download and compile the sdk](https://fli---v1.webflow.io/support)
- Python 3.13+

## Installation

```bash
pip install -e .
```

## Configuration

Example config:

```yaml
filterwheel:
    type: FLIFilterWheel
    name: main
    sdk_library_path: "/home/name/chimera-fli/libfli.so"
    filter_wheel_model: "FLI CFW-7-7"
    filters: "R G B Ha OIII SII CLEAR"
    fake: false # optional, default: false
    move_timeout_s: 30 # optional, default: 30 seconds
```

Set `fake: true` to run without hardware (uses the built-in mock for testing).
