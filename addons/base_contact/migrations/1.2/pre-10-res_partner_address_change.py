# -*- coding: utf8 -*-

__name__ = "res.partner.adress: for each address it should create a contact with the name of the address"

def migrate(cr, version):
    generate_contact(cr)

def generate_contact(cr):
    cr.execute("""DROP TRIGGER  IF EXISTS contactjob on res_partner_contact;
                        DROP LANGUAGE  IF EXISTS  plpgsql CASCADE;
                        CREATE LANGUAGE plpgsql ;
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
    cr.commit()

    cr.execute("INSERT into res_partner_contact (name, title, email, first_name, website)  (SELECT coalesce(name, 'Noname'), title, email, function , to_char(id, '99999999') from res_partner_address)")
    cr.commit()
    cr.execute("DROP TRIGGER  IF EXISTS contactjob  on res_partner_contact")
    cr.execute("DROP LANGUAGE  IF EXISTS  plpgsql CASCADE;")
    cr.execute("DROP FUNCTION IF EXISTS  add_to_job()")
    cr.commit()