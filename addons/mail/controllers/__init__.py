# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import attachment
from . import google_translate
from . import guest
from . import link_preview
from . import mail
from . import mailbox
from . import message_reaction
from . import thread
from . import webclient
from . import webmanifest

# after mail specifically as discuss module depends on mail
from . import discuss
