# When testrunner.py is invoked with --coverage, it puts this first
# on the path as per https://coverage.readthedocs.io/en/coverage-4.0b3/subprocess.html.
# Note that this disables other sitecustomize.py files.
import coverage
try:
    coverage.process_startup()
except coverage.CoverageException as e:
    if str(e) == "Can't support concurrency=greenlet with PyTracer, only threads are supported":
        pass
    else:
        import traceback
        traceback.print_exc()
        raise
except:
    import traceback
    traceback.print_exc()
    raise
