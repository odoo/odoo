from . import models
from . import tests

def _l10n_es_pos_set_sequence_post_init_hook(env):
    env['pos.config'].search([])._set_simplified_l10n_es_sequence()
