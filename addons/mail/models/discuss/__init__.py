# Part of Odoo. See LICENSE file for full copyright and licensing details.

# mail
from . import mail_message

# discuss
from . import discuss_channel_member
from . import discuss_channel_rtc_session
from . import discuss_channel
from . import discuss_gif_favorite
from . import discuss_voice_metadata
from . import mail_guest

# odoo models
from . import ir_attachment
from . import ir_binary
from . import ir_http
from . import ir_websocket
from . import res_groups
from . import res_partner
from . import res_users


# monkey patch environment to add guest-based environment properties
from odoo.api import Environment
from odoo.tools import lazy_property

@lazy_property
def guest(self):
    """Return the current guest, if defined """
    print("proutichou guest")
    guest = self.context.get('guest')
    return guest

Environment.guest = guest
