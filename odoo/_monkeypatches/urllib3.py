from urllib3 import PoolManager

orig_pool_init = PoolManager.__init__


def pool_init(self, *args, **kwargs):
    orig_pool_init(self, *args, **kwargs)
    self.pool_classes_by_scheme = {**self.pool_classes_by_scheme}


def patch_module():
    PoolManager.__init__ = pool_init
