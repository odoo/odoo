from . import models
from . import wizard

def _todo_uninstall(env):
    # The record rule project.task_visibility_rule needs to apply to all rights and not just read after uninstallation
    project_task_visibility_rule_rec = env.ref("project.task_visibility_rule")
    project_task_visibility_rule_rec.write({
        'perm_create': True,
        'perm_unlink': True,
        'perm_write': True,
    })
