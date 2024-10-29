from gevent import monkey; monkey.patch_all()
import threading


localdata = threading.local()
localdata.x = "hello"
assert localdata.x == 'hello'
success = []


def func():
    try:
        getattr(localdata, 'x')
        raise AssertionError('localdata.x must raise AttributeError')
    except AttributeError:
        pass
    # We really want to check this is exactly an empty dict,
    # not just anything falsey
    # pylint:disable=use-implicit-booleaness-not-comparison
    assert localdata.__dict__ == {}, localdata.__dict__
    success.append(1)

t = threading.Thread(None, func)
t.start()
t.join()
assert success == [1], 'test failed'
assert localdata.x == 'hello'
