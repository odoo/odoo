# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

SCAN_MAX_COUNT = 1000

def find_in_html_field(env, html_escaped_likes):
    """ Returns models where the likes appear inside HTML fields.

        :param env: env
        :param html_escaped_likes: array of string to include as values of
               domain 'like'. Values must be HTML escaped.

        :returns PNG image converted from given font
    """
    all_matches = []
    big_models = []
    sudo_models = []
    for model_name, field_name, domain, requires_full_scan in env['base']._get_examined_html_fields():
        if not requires_full_scan:
            if model_name in big_models:
                continue
            if env[model_name].sudo().with_context(active_test=False).search_count([]) > SCAN_MAX_COUNT:
                big_models.append(model_name)
                continue
        likes = [(field_name, 'like', like) for like in html_escaped_likes]
        domain.extend([
            *(['|'] * (len(likes) - 1)),
            *likes,
        ])
        matches = env[model_name]
        if matches.check_access_rights('read', raise_exception=False):
            matches = matches.with_context(active_test=False).search(domain)
            all_matches.append(matches)
            continue
        if model_name in sudo_models:
            continue
        sudo_matches = env[model_name].sudo().with_context(active_test=False).search(domain, limit=1)
        if sudo_matches:
            sudo_models.append(model_name)
    return {
        'matches': all_matches,
        'skipped_models': big_models,
        'access_models': sudo_models,
    } if matches or big_models or sudo_models else None
