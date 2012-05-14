what is shown
==============
 - for every opportunities, sale orders and invoices which are related to partner show in the partner view


how it is done
===============
 - _inherit = 'mail.thread'
 - Override def message_load_ids method based on search by the partner_id and res_id
