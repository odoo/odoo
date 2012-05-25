from openerp.osv import osv, fields

class crm_contact_us(osv.TransientModel):
    """ Create new leads through the "contact us" form """
    _name = 'portal_crm.crm_contact_us'
    _description = 'Contact form for the portal'
    _inherit = 'crm.lead'

    def create(self, cr, uid, values, context=None):
        """ 
        Since they potentially sensitive, we don't want any user to be able to 
        read datas generated through this module.  That's why we'll write those 
        information in the crm.lead table and leave blank entries in the 
        portal_crm.crm_contact_us table.  This is why the create() method is 
        overridden.
        """
        crm_lead = self.pool.get('crm.lead')
        
        """ 
        Because of the complex inheritance of the crm.lead model and the other 
        models implied (like mail.thread, among others, that performs a read 
        when its create() method is called (in method message_get_subscribers()), 
        it is quite complicated to set proper rights for this object.  
        Therefore, user #1 will perform the creation until a better workaround 
        is figured out.
        """
        crm_lead.create(cr, 1, dict(values,user_id=uid), context)

        """ Create an empty record in the portal_crm.crm_contact_us table """
        return super(crm_contact_us, self).create(cr, uid, {})

    def submit(self, cr, uid, ids, context=None):
        """ When the form is submitted, redirect the user to a "Thanks" message """
        return {'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': self._name,
                'res_id': ids[0],
                'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal_crm', 'wizard_contact_form_view_thanks')[1]
               }
