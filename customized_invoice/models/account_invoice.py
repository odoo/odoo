# -*- coding: utf-8 -*-
from openerp import models, fields, api

class customized_invoice(models.Model):
	_inherit=["account.invoice"]

	@api.model
	def _default_template(self):
	    company_obj = self.env['res.company']
	    company = self.env['res.users'].browse([self.env.user.id]).company_id
	    if not company.template_invoice:
		def_tpl = self.env['ir.ui.view'].search([('name', 'like', 'Template' ), ('type', '=', 'qweb')], order='id asc', limit=1)
                company.write({'template_invoice': def_tpl.id})
	    return company.template_invoice or self.env.ref('account.report_invoice_document')
	
	@api.model
	def _default_odd(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).odd

	@api.model
	def _default_even(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).even

	@api.model
	def _default_theme_color(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).theme_color

	@api.model
	def _default_theme_txt_color(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).theme_txt_color

	@api.model
	def _default_name_color(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).name_color

	@api.model
	def _default_cust_color(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).cust_color

	@api.model
	def _default_text_color(self):
	    company_id = self.env['res.users'].browse([self.env.user.id]).company_id
	    return self.env['res.company'].browse([company_id.id]).text_color

	
 	invoice_logo = fields.Binary("Logo", attachment=True,
             help="This field holds the image used as logo for the invoice, if non is uploaded, the default logo define in the copmany settings will be used")
	template_id = fields.Many2one('ir.ui.view', 'Invoice Template', default=_default_template,required=True, 
		domain="[('type', '=', 'qweb'), ('name', 'like', 'Template' )]")
	odd = fields.Char('Odd parity Color', size=7, required=True, default=_default_odd, help="The background color for Odd lines in the invoice")	
	even = fields.Char('Even parity Color', size=7, required=True, default=_default_even, help="The background color for Even lines in the invoice" )	
	theme_color = fields.Char('Theme Color', size=7, required=True, default=_default_theme_color, help="The Main Theme color of the invoice. Normally this\
			 should be one of your official company colors")	
	theme_txt_color = fields.Char('Theme Text Color', size=7, required=True, default=_default_theme_txt_color, 
			help="The Text color of the areas with theme color. This should not be the same the theme color")	
	text_color = fields.Char('Text Color', size=7, required=True, default=_default_text_color, help="The Text color of the invoice. Normally this\
			 should be one of your official company colors or default HTML text color")	
	name_color = fields.Char('Company Name Color', size=7, required=True, default=_default_name_color, help="The Text color of the Company Name. \
			Normally thisshould be one of your official company colors or default HTML text color")	
	cust_color = fields.Char('Customer Name Color', size=7, required=True, default=_default_name_color, help="The Text color of the Customer Name. \
			Normally this should be one of your official company colors or default HTML text color")	

	##Override invoice_print method in original invoice class in account module
	@api.multi
	def invoice_print(self):
            """ Print the invoice and mark it as sent, so that we can see more
               easily the next step of the workflow
	       This Method overrides the one in the original invoice class
            """
            self.ensure_one()
            self.sent = True
            return self.env['report'].get_action(self, 'customized_invoice.my_invoice')

