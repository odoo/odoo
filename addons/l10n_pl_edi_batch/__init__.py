from . import models
from . import tools


def uninstall_hook(env):
    """ Without the batches, the single bill download takes over again """
    if single_download_cron := env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills', raise_if_not_found=False):
        single_download_cron.active = True
