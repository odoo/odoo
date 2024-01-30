# -*- coding: utf-8 -*-


def rename_tag(cr, old_tag, new_tag):
    cr.execute(
        """UPDATE ir_model_data
           SET name=%s
           WHERE module='l10n_de' AND name=%s
        """,
        (new_tag, old_tag),
    )


def migrate(cr, version):
    # By deleting tag B from ir_model_data we ensure that the ORM won't try to remove this record.
    # This is done because the tag might be already used as a FK somewhere else.
    cr.execute(
        """DELETE FROM ir_model_data
           WHERE module='l10n_de'
           AND name='tag_de_liabilities_bs_B'
        """
    )

    # As some people already upgraded, they will have renamed the C_1 tag to B_1. This doesn't come from the script but from the
    # account_account_tags_data.xml. If they try to run this script now in the fix they get the error that B_1 already exists.
    # To fix this we can check if it exists or not, and if it does then we don't run the script. This means that the ones
    # that upgraded won't have the old tags data transferred to the new tags but they will still be able to have the updated sheet.
    cr.execute(
        """SELECT 1 FROM ir_model_data
           WHERE module='l10n_de' AND name='tag_de_liabilities_bs_B_1'
        """)
    if cr.rowcount:
        # If the script didn't run, we should remove the tags that have been replaced from ir_model_data too so they're
        # not deleted by the ORM if they were already used.
        cr.execute(
            """DELETE FROM ir_model_data
               WHERE module='l10n_de'
               AND name IN ('tag_de_liabilities_bs_F', 'tag_de_liabilities_bs_D_1', 'tag_de_liabilities_bs_D_2',
               'tag_de_liabilities_bs_D_3', 'tag_de_liabilities_bs_D_4', 'tag_de_liabilities_bs_D_5',
               'tag_de_liabilities_bs_D_6', 'tag_de_liabilities_bs_D_7', 'tag_de_liabilities_bs_D_8')
            """
        )
        return
    rename_tag(cr, "tag_de_liabilities_bs_C_1", "tag_de_liabilities_bs_B_1")
    rename_tag(cr, "tag_de_liabilities_bs_C_2", "tag_de_liabilities_bs_B_2")
    rename_tag(cr, "tag_de_liabilities_bs_C_3", "tag_de_liabilities_bs_B_3")
    rename_tag(cr, "tag_de_liabilities_bs_D_1", "tag_de_liabilities_bs_C_1")
    rename_tag(cr, "tag_de_liabilities_bs_D_2", "tag_de_liabilities_bs_C_2")
    rename_tag(cr, "tag_de_liabilities_bs_D_3", "tag_de_liabilities_bs_C_3")
    rename_tag(cr, "tag_de_liabilities_bs_D_4", "tag_de_liabilities_bs_C_4")
    rename_tag(cr, "tag_de_liabilities_bs_D_5", "tag_de_liabilities_bs_C_5")
    rename_tag(cr, "tag_de_liabilities_bs_D_6", "tag_de_liabilities_bs_C_6")
    rename_tag(cr, "tag_de_liabilities_bs_D_7", "tag_de_liabilities_bs_C_7")
    rename_tag(cr, "tag_de_liabilities_bs_D_8", "tag_de_liabilities_bs_C_8")
    rename_tag(cr, "tag_de_liabilities_bs_E", "tag_de_liabilities_bs_D")
    rename_tag(cr, "tag_de_liabilities_bs_F", "tag_de_liabilities_bs_E")
