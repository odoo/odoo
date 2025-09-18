"""Thread-local request state."""

import contextlib

import werkzeug.local

# Thread local global request object
_request_stack = werkzeug.local.LocalStack()
request = _request_stack()


@contextlib.contextmanager
def borrow_request():
    """Get the current request and unexpose it from the local stack."""
    req = _request_stack.pop()
    try:
        yield req
    finally:
        _request_stack.push(req)
