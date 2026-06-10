from odoo.http import Controller, route
from odoo.tools import _
import random
from time import sleep


class ContactController(Controller):
    @route(
        "/website/team_board_contact",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def send_message(self):
        sleep(0.5)
        return random.choice([
            {"success": False, "statusMsg": _("Could not send your message.")},
            {"success": True, "statusMsg": _("Your message has been sent.")}
        ])
