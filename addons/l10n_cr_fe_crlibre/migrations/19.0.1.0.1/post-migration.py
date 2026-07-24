def migrate(cr, version):
    # Antes de esta version, FE (tipo 01) y NC (tipo 03) compartian una unica
    # secuencia de consecutivo ('l10n_cr_fe.consecutivo.fe.<company>'). Al
    # separarla por tipo de documento, la secuencia nueva de FE se creaba
    # reiniciando en 1 aunque la empresa ya tuviera consecutivos usados ante
    # Hacienda bajo la secuencia vieja, causando un rechazo por numero de
    # consecutivo duplicado. Esto adelanta la secuencia nueva de FE hasta
    # donde iba la vieja, para cada empresa que ya la tuviera en uso.
    cr.execute("""
        SELECT company_id, number_next
          FROM ir_sequence
         WHERE code LIKE 'l10n_cr_fe.consecutivo.fe.%'
           AND company_id IS NOT NULL
    """)
    for company_id, legacy_next in cr.fetchall():
        new_code = 'l10n_cr_fe.consecutivo.01.%s' % company_id
        cr.execute("SELECT id, number_next FROM ir_sequence WHERE code = %s", (new_code,))
        row = cr.fetchone()
        if row and row[1] < legacy_next:
            cr.execute("UPDATE ir_sequence SET number_next = %s WHERE id = %s", (legacy_next, row[0]))
