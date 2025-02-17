from . import demo
from . import models
from . import wizard


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()
