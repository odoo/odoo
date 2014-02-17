
from openerp.osv import osv, fields

class crm_lead_to_project_issue_wizard(osv.TransientModel):
    """ wizard to convert a Lead into a Project Issue and move the Mail Thread """

    def action_lead_to_project_issue(self, cr, uid, ids, context=None):
        # get the wizards
        wizards = self.browse(cr, uid, ids, context=context)
        lead_model = self.pool.get("crm.lead")
        issue_model = self.pool.get("project.issue")

        for wizard in wizards:
            # get the lead to transform
            lead = lead_model.browse(cr, uid, wizard.lead_id.id, context=context)
            # create new project.issue
            vals = {}
            vals["name"] = lead.name
            vals["description"] = lead.description
            vals["email_from"] = lead.email_from
            vals["partner_id"] = lead.partner_id.id
            vals["project_id"] = wizard.project_id.id
            issue_id = issue_model.create(cr, uid, vals, context=None) 
            # move the mail thread
            lead_model.transform_model_messages(cr, uid, wizard.lead_id.id, issue_id, "project.issue", context=context)
            # delete the lead
            lead_model.unlink(cr, uid, [wizard.lead_id.id], context=None)
        return False


    _name = "crm.lead2projectissue.wizard"

    _columns = {
        "lead_id" : fields.many2one("crm.lead","Lead", domain=[("type","=","lead")]),
        "project_id" : fields.many2one("project.project", "Project", domain=[("use_issues","=",True)])
    }