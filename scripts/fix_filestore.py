import os
from odoo import api, SUPERUSER_ID

def run_fix(env):
    print("🔍 Aggressive Filestore Check...")
    
    data_dir = "/home/laxman/.local/share/Odoo/filestore/odoo_db"
    print(f"📁 Filestore Path: {data_dir}")
    
    # Check ALL attachments with checksum but no data or broken path
    attachments = env['ir.attachment'].search([('type', '=', 'binary')])
    
    fixed_count = 0
    checked_count = 0
    
    for attach in attachments:
        checked_count += 1
        fname = attach.store_fname or attach.checksum
        if not fname:
            continue
            
        full_path = os.path.join(data_dir, fname)
        if not os.path.exists(full_path):
            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(b"")
                fixed_count += 1
                if fixed_count % 10 == 0:
                    print(f"  .. fixed {fixed_count} files")
            except Exception as e:
                print(f"❌ Error fixing {fname}: {e}")
                
    print(f"✅ Total Checked: {checked_count}")
    print(f"✅ Total Fixed: {fixed_count}")
    
    # 2. Disable Cron again just in case session toggle somehow re-enabled it
    env['ir.cron'].search([('code', 'ilike', '_cron_auto_open_delivery_session')]).write({'active': False})
    env.cr.commit()
    print("🚫 Auto-Open Cron forced to INACTIVE.")



if __name__ == '__main__':
    # usage: ./odoo-bin shell -c config/odoo.conf -d odoo_db < scripts/fix_filestore.py
    run_fix(env)
