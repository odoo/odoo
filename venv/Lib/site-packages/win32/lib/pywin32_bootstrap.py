# Imported by pywin32.pth to bootstrap the pywin32 environment in "portable"
# environments or any other case where the post-install script isn't run.
#
# In short, there's a directory installed by pywin32 named 'pywin32_system32'
# with some important DLLs which need to be found by Python when some pywin32
# modules are imported.


try:
    import pywin32_system32
except ImportError:  # Python ≥3.6: replace ImportError with ModuleNotFoundError
    pass
else:
    import os

    # We're guaranteed only that __path__: Iterable[str]
    # https://docs.python.org/3/reference/import.html#path-attributes-on-modules
    for path in pywin32_system32.__path__:
        if os.path.isdir(path):
            os.add_dll_directory(path)
            break
