from . import models
from . import wizards


def uninstall_hook(env):
    teams = env["team.team"].search(
        [("use_sale", "=", True), ("use_opportunities", "=", False)]
    )
    teams.write({"use_opportunities": True})
