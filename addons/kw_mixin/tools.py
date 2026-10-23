import logging

_logger = logging.getLogger(__name__)


def use_fname(*deco_args):
    def decorator(func, *aa):
        def wrapper(*args, **kwargs):
            self = args[0]
            self.ensure_one()
            f = deco_args[0] if deco_args else 'code'
            fname = f'{func.__name__}_{getattr(self, f)}'
            if hasattr(self, fname):
                return getattr(self, fname)(*args[1:], **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def urljoin(*args):
    return "/".join(map(lambda x: str(x).strip('/'), args))
