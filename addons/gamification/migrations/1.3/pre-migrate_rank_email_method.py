from odoo.tools.module_data import rename_in_stored_expressions


def migrate(cr, version):
    if not version:
        return
    # The rank email is noupdate and its body can contain translated/customized
    # calls. The method name is unique across models, including related users.
    rename_in_stored_expressions(
        cr,
        "get_gamification_redirection_data",
        "prepare_rank_email_links",
        unique=True,
    )
