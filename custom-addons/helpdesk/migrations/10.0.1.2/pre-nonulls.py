# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("""
        UPDATE helpdesk_sla
           SET time_days = COALESCE(time_days, 0),
               time_hours = COALESCE(time_hours, 0),
               time_minutes = COALESCE(time_minutes, 0)
    """)
