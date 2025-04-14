def migrate(cr, version):
    cr.execute("""
        UPDATE ir_sequence iseq
        SET implementation = 'no_gap'
        FROM pos_config pconfig,res_company rcomp, res_country rcount, res_partner rpart
        WHERE rcount.code in ('FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF', 'BL', 'PM', 'YT', 'WF')
        AND rpart.country_id = rcount.id
        AND rcomp.partner_id = rpart.id
        AND pconfig.company_id = rcomp.id
        AND (pconfig.sequence_id = iseq.id or pconfig.sequence_line_id = iseq.id)
        AND iseq.implementation = 'standard'
        """)
