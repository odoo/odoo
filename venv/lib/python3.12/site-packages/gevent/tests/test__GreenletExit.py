from gevent import GreenletExit

assert issubclass(GreenletExit, BaseException)
assert not issubclass(GreenletExit, Exception)
