# test__import_wait.py calls this via an import statement,
# so all of this is happening with import locks held (especially on py2)
import gevent


def fn2():
    return 2


# A blocking function doesn't raise LoopExit
def fn():
    return gevent.wait([gevent.spawn(fn2), gevent.spawn(fn2)])

gevent.spawn(fn).get()


# Marshalling the traceback across greenlets doesn't
# raise LoopExit
def raise_name_error():
    raise NameError("ThisIsExpected")

try:
    gevent.spawn(raise_name_error).get()
    raise AssertionError("Should fail")
except NameError as e:
    x = e
