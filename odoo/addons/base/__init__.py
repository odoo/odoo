from . import models
from . import report
from . import wizard


def post_init(env):
    """Rewrite ICP's to force groups"""
    env["ir.config_parameter"].init(force=True)
