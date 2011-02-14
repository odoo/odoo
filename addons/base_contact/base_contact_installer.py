# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

class base_contact_installer(osv.osv_memory):
    _name = 'base.contact.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'name': fields.char('Name', size=64),
        'migrate': fields.boolean('Migrate', help="If you select this, all addresses will be migrated."),
    }

    def execute(self, cr, uid, ids, context=None):
        """
        This function is used to create contact and address from existing partner address
        """
        obj = self.pool.get("base.contact.installer").browse(cr, uid, uid, context=context)
        if obj.migrate:
            # Enable PL/pgSQL if not enabled yet in the database
            cr.execute("SELECT 1 FROM pg_language WHERE lanname = 'plpgsql'")
            if not cr.fetchone():
                cr.execute("CREATE LANGUAGE plpgsql;")

            cr.execute("""DROP TRIGGER IF EXISTS contactjob on res_partner_contact;
                          CREATE OR REPLACE FUNCTION add_to_job() RETURNS TRIGGER AS $contactjob$
                            DECLARE
                            new_name varchar;
                            new_phonenum varchar;
                            BEGIN
                               IF(TG_OP='INSERT') THEN
                               INSERT INTO res_partner_job(contact_id, address_id, function, state) VALUES(NEW.id, NEW.website::integer,NEW.first_name, 'current');
                               UPDATE res_partner_contact set first_name=Null, website=Null, active=True where id=NEW.id;
                            END IF;
                            RETURN NEW;
                            END;
                          $contactjob$ LANGUAGE plpgsql;
                          CREATE TRIGGER contactjob AFTER INSERT ON res_partner_contact FOR EACH ROW EXECUTE PROCEDURE add_to_job();""")

            cr.execute("INSERT into res_partner_contact (name, title, email, first_name, website)  (SELECT coalesce(name, 'Noname'), title, email, function , to_char(id, '99999999') from res_partner_address)")

            cr.execute("DROP TRIGGER  IF EXISTS contactjob  on res_partner_contact")

            cr.execute("DROP FUNCTION IF EXISTS  add_to_job()")

base_contact_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
