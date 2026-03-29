# -*- coding: utf-8 -*-
from . import models
from . import controllers

def create_default_time_slots(cr, registry):
    """Create default time slots (every hour from 00:00 to 23:00)"""
    from odoo.api import Environment
    
    env = Environment(cr, registry.uid, {})
    
    # Check if time slots already exist
    existing_slots = env['tuition.time.slot'].search([])
    
    if not existing_slots:
        # Create time slots for every hour (00:00 to 23:00)
        time_slots = []
        for hour in range(24):
            for minute in [0, 30]:  # 00:00, 00:30, 01:00, 01:30, etc.
                time_slots.append({
                    'hour': hour,
                    'minute': minute,
                    'name': f"{hour:02d}:{minute:02d}"
                })
        
        for slot in time_slots:
            env['tuition.time.slot'].create(slot)
        
        cr.commit()
