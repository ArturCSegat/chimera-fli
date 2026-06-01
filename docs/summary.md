# FLI Filter Wheel — API Reference

> Extracted from FLI SDK v1.40 (`libfli`). Language-agnostic. Intended as the source of truth for ctypes bindings.

---

## Conventions

- All functions return `long` — **0 on success, non-zero on failure**
- On failure, negate the return value to get a system `errno` code
- All device operations require a `flidev_t` handle obtained from `FLIOpen`
- String output parameters are caller-allocated buffers with an accompanying `size_t len`
- Pointer output parameters (`long*`, `double*`) are caller-allocated; the function writes the result into them

---

## Types

| C Type | Width | Description |
|--------|-------|-------------|
| `flidev_t` | `long` | Opaque device handle. Invalid/uninitialized value is `-1` |
| `flidomain_t` | `long` | Bitwise OR of an interface constant and a device-type constant |

### `flidomain_t` — Interface Constants

| Name | Description |
|------|-------------|
| `FLIDOMAIN_PARALLEL_PORT` | Parallel port interface |
| `FLIDOMAIN_USB` | USB interface |
| `FLIDOMAIN_SERIAL` | Serial interface |
| `FLIDOMAIN_INET` | Network interface |

### `flidomain_t` — Device Type Constants

| Name | Description |
|------|-------------|
| `FLIDEVICE_CAMERA` | CCD camera |
| `FLIDOMAIN_FILTERWHEEL` | Filter wheel |
| `FLIDOMAIN_FOCUSER` | Focuser |

**Usage:** combine one interface and one device type with bitwise OR, e.g. `FLIDOMAIN_USB | FLIDOMAIN_FILTERWHEEL`.

> ⚠️ Numeric values for these constants are not in the PDF documentation. Read them directly from `libfli.h` on the target system.

### Debug Level Constants (`flidebug_t`)

| Name | Description |
|------|-------------|
| `FLIDEBUG_NONE` | Disable debug output |
| `FLIDEBUG_FAIL` | Log failures only |
| `FLIDEBUG_WARN` | Log warnings and failures |
| `FLIDEBUG_INFO` | Log everything (most verbose) |

---

## Functions

---

### `FLIList`

Enumerate all attached devices matching a domain. Returns a NULL-terminated array of strings. Each string has the format `"filename;ModelName"` — split on `;` to get the filename needed by `FLIOpen`.

**Must be followed by `FLIFreeList` to release memory.**

```
FLIList(domain, names) -> long

domain  flidomain_t        in   Interface + device type flags
names   char***            out  Pointer to a NULL-terminated array of "filename;model" strings
```

---

### `FLIFreeList`

Free the device name list allocated by `FLIList`.

```
FLIFreeList(names) -> long

names   char**   in   Pointer returned by FLIList
```

---

### `FLICreateList`

Begin iterator-style device enumeration. Must be paired with `FLIDeleteList`. Call before `FLIListFirst`.

```
FLICreateList(domain) -> long

domain  flidomain_t   in   Interface + device type flags. Pass 0 to search all domains (must still include device type)
```

---

### `FLIDeleteList`

Release the device list created by `FLICreateList`.

```
FLIDeleteList() -> long
```

---

### `FLIListFirst`

Get the first device from the list created by `FLICreateList`.

```
FLIListFirst(domain, filename, fnlen, name, namelen) -> long

domain    flidomain_t*   out   Domain of the found device
filename  char*          out   Device filename (use with FLIOpen). Caller-allocated buffer
fnlen     size_t         in    Size of filename buffer in bytes
name      char*          out   Model/user name of the device. Caller-allocated buffer
namelen   size_t         in    Size of name buffer in bytes
```

Returns non-zero (no error raised) when list is exhausted.

---

### `FLIListNext`

Advance to the next device. Same signature as `FLIListFirst`. Call repeatedly until non-zero is returned.

```
FLIListNext(domain, filename, fnlen, name, namelen) -> long

(same parameters as FLIListFirst)
```

---

### `FLIOpen`

Open a device and obtain a handle. The handle is used in all subsequent calls.

```
FLIOpen(dev, name, domain) -> long

dev     flidev_t*     out   Receives the device handle
name    char*         in    Device filename (from FLIList or FLIListFirst)
domain  flidomain_t   in    Must match the domain used during enumeration
```

---

### `FLIClose`

Close a device handle and release associated resources.

```
FLIClose(dev) -> long

dev   flidev_t   in   Handle to close
```

---

### `FLIGetModel`

Read the model name string of an open device into a caller-allocated buffer.

```
FLIGetModel(dev, model, len) -> long

dev    flidev_t   in    Open device handle
model  char*      out   Caller-allocated buffer to receive model string
len    size_t     in    Size of model buffer in bytes
```

---

### `FLIGetFWRevision`

Read the firmware revision number of an open device.

```
FLIGetFWRevision(dev, fwrev) -> long

dev    flidev_t   in    Open device handle
fwrev  long*      out   Receives firmware revision number
```

---

### `FLIGetHWRevision`

Read the hardware revision number of an open device.

```
FLIGetHWRevision(dev, hwrev) -> long

dev    flidev_t   in    Open device handle
hwrev  long*      out   Receives hardware revision number
```

---

### `FLIGetLibVersion`

Read the SDK library version string into a caller-allocated buffer.

```
FLIGetLibVersion(ver, len) -> long

ver   char*    out   Caller-allocated buffer to receive version string
len   size_t   in    Size of ver buffer in bytes
```

---

### `FLIGetFilterCount`

Get the total number of filter positions on the wheel.

```
FLIGetFilterCount(dev, filter) -> long

dev     flidev_t   in    Open filter wheel handle
filter  long*      out   Receives the number of filter positions
```

---

### `FLISetFilterPos`

Command the wheel to move to a given position. **Returns after initiating the move — the motor may still be turning.** Poll `FLIGetStepsRemaining` to confirm completion.

```
FLISetFilterPos(dev, filter) -> long

dev     flidev_t   in   Open filter wheel handle
filter  long       in   Target position, 0-indexed
```

---

### `FLIGetFilterPos`

Read the current filter wheel position.

```
FLIGetFilterPos(dev, filter) -> long

dev     flidev_t   in    Open filter wheel handle
filter  long*      out   Receives current position, 0-indexed
```

---

### `FLIGetStepsRemaining`

Get the number of motor steps still pending. Returns 0 when the motor has stopped. Use this to poll after `FLISetFilterPos`.

```
FLIGetStepsRemaining(dev, steps) -> long

dev    flidev_t   in    Open filter wheel handle
steps  long*      out   Receives the number of steps remaining
```

---

### `FLIStepMotor`

Move the motor a raw number of steps. **Blocking** — returns only after the move completes.

```
FLIStepMotor(dev, steps) -> long

dev    flidev_t   in   Open filter wheel or focuser handle
steps  long       in   Number of steps to move (sign determines direction)
```

---

### `FLIStepMotorAsync`

Move the motor a raw number of steps. **Non-blocking** — returns immediately. Use `FLIGetStepsRemaining` or `FLIGetStepperPosition` to monitor progress.

```
FLIStepMotorAsync(dev, steps) -> long

dev    flidev_t   in   Open filter wheel or focuser handle
steps  long       in   Number of steps to move
```

---

### `FLIGetStepperPosition`

Read the raw stepper motor position counter.

```
FLIGetStepperPosition(dev, position) -> long

dev       flidev_t   in    Open filter wheel or focuser handle
position  long*      out   Receives current stepper position
```

---

### `FLILockDevice`

Acquire an exclusive lock (mutex) on the device. Blocks other processes or handles from accessing it until unlocked.

```
FLILockDevice(dev) -> long

dev   flidev_t   in   Open device handle
```

---

### `FLIUnlockDevice`

Release a previously acquired exclusive lock.

```
FLIUnlockDevice(dev) -> long

dev   flidev_t   in   Open device handle
```

---

### `FLISetDebugLevel`

Enable or configure SDK debug logging.

- **Linux:** output goes to `syslog`; `host` parameter is ignored
- **Windows:** output goes to `C:\FLIDBG.TXT` if that file exists; `host` is the filename otherwise

```
FLISetDebugLevel(host, level) -> long

host   char*        in   Log destination filename (Windows). Pass NULL on Linux
level  flidebug_t   in   One of: FLIDEBUG_NONE, FLIDEBUG_FAIL, FLIDEBUG_WARN, FLIDEBUG_INFO
```

---

## Call Sequence — Filter Wheel

```
Enumerate
  FLICreateList(domain)
    FLIListFirst(...)
    FLIListNext(...)   ← repeat until non-zero
  FLIDeleteList()

Open
  FLIOpen(&dev, filename, domain)

Query
  FLIGetModel(dev, ...)
  FLIGetFilterCount(dev, ...)

Move
  FLILockDevice(dev)
    FLISetFilterPos(dev, position)
    loop: FLIGetStepsRemaining(dev, &steps) until steps == 0
    FLIGetFilterPos(dev, &pos)        ← verify
  FLIUnlockDevice(dev)

Close
  FLIClose(dev)
```

---

## Output Parameter Summary

These are the parameters that require a pointer to caller-allocated storage in ctypes (`byref` or `POINTER`):

| Function | Output Parameter | C Type | ctypes type |
|----------|-----------------|--------|-------------|
| `FLIOpen` | `dev` | `flidev_t*` | `POINTER(c_long)` |
| `FLIListFirst` / `FLIListNext` | `domain` | `flidomain_t*` | `POINTER(c_long)` |
| `FLIListFirst` / `FLIListNext` | `filename` | `char*` | `create_string_buffer(n)` |
| `FLIListFirst` / `FLIListNext` | `name` | `char*` | `create_string_buffer(n)` |
| `FLIGetModel` | `model` | `char*` | `create_string_buffer(n)` |
| `FLIGetLibVersion` | `ver` | `char*` | `create_string_buffer(n)` |
| `FLIGetFWRevision` | `fwrev` | `long*` | `byref(c_long())` |
| `FLIGetHWRevision` | `hwrev` | `long*` | `byref(c_long())` |
| `FLIGetFilterCount` | `filter` | `long*` | `byref(c_long())` |
| `FLIGetFilterPos` | `filter` | `long*` | `byref(c_long())` |
| `FLIGetStepsRemaining` | `steps` | `long*` | `byref(c_long())` |
| `FLIGetStepperPosition` | `position` | `long*` | `byref(c_long())` |
