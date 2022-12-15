

def load_translations(env):
    """Load template translations."""
    env.ref(
        'l10n_lt.account_chart_template_lithuania').process_coa_translations()
