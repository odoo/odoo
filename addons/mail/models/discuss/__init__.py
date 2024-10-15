# Part of Odoo. See LICENSE file for full copyright and licensing details.

# mail
from .mail_message import MailMessage

# discuss
from .discuss_channel_member import DiscussChannelMember
from .discuss_channel_rtc_session import DiscussChannelRtcSession
from .discuss_channel import DiscussChannel
from .discuss_gif_favorite import DiscussGifFavorite
from .discuss_voice_metadata import DiscussVoiceMetadata
from .mail_guest import MailGuest

# odoo models
from .bus_listener_mixin import BusListenerMixin
from .ir_attachment import IrAttachment
from .ir_binary import IrBinary
from .ir_websocket import IrWebsocket
from .res_groups import ResGroups
from .res_partner import ResPartner
from .res_users import ResUsers
