from . import models
from . import receipt


def _l10n_es_edi_pos_post_init(env):
    env['pos.config'].search([])._l10n_es_pos_create_refund_sequence()
