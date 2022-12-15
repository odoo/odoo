from . import models


def load_translations(env):
    env.ref('l10n_eg.egypt_chart_template_standard').process_coa_translations()
