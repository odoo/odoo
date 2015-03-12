# -*- coding: utf-8 -*-
import base64
import re
import time

from openerp import api, fields, models
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _


class PrintProvider(models.Model):
    """ Print Provider Base Model. Each specific provider can extend the model by adding
        its own fields, using the provider_name (provider field) as a prefix for the new
        fields and method.
    """

    _name = 'print.provider'
    _description = 'Print Provider'

    def _get_providers(self):
        return []


    name = fields.Char("Name", required=True)
    environment = fields.Selection([('test', 'Test'), ('production', 'Production')], "Environment", default='test')
    provider = fields.Selection(selection='_get_providers', string='Provider', required=True)
    balance = fields.Float("Credit", digits=(16, 2))

    @api.multi
    def update_account_data(self):
        """ Update the provider account data. Requires a fetch to the provider server. """
        self.ensure_one()
        getattr(self, '%s_update_account_data' % self.provider, lambda: None)()

    def check_configuration(self):
        """ Check if the credentials of the current provider are filled. If not, raise a warning. """
        self.ensure_one()
        getattr(self, '%s_check_configuration' % self.provider, lambda: None)()


class PrintOrder(models.Model):
    """ Print Order Model. Each specific provider can extend the model by adding
        its own fields, using the same convertion of the print.provider model.
    """

    _name = 'print.order'
    _rec_name = 'id'
    _description = 'Print Order'
    _order = 'sent_date desc'


    def _default_print_provider(self):
        return self.env['ir.values'].get_default('print.order', 'provider_id')

    create_date = fields.Datetime('Creation Date', readonly=True)
    sent_date = fields.Datetime('Sending Date', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id, readonly=True, states={'draft':[('readonly', False)]})
    user_id = fields.Many2one('res.users', 'Author', default=lambda self: self.env.user)
    provider_id = fields.Many2one('print.provider', 'Print Provider', required=True, default=_default_print_provider, readonly=True, states={'draft':[('readonly', False)]})

    ink = fields.Selection([('BW', 'Black & White'), ('CL', 'Colour')], "Ink", default='BW', states={'sent':[('readonly', True)]})
    paper_weight = fields.Integer("Paper Weight", default=80, readonly=True)
    res_id = fields.Integer('Object ID', required=True)
    res_model = fields.Char('Model Name', required=True)

    attachment_id = fields.Many2one('ir.attachment', 'PDF', states={'sent':[('readonly', True)]}, domain=[('mimetype', '=', 'application/pdf')])
    nbr_pages = fields.Integer("Number of Pages", readonly=True, default=0)
    price = fields.Float("Cost to Deliver", digits=(16, 2), readonly=True, default=0.0)

    error_message = fields.Text('Error Message', readonly=True)

    state = fields.Selection([
            ('draft', 'Draft'),
            ('ready', 'Ready'),
            ('sent', 'Sent'),
            ('error', 'Failed'),
        ], string='Status', default='draft', readonly=True, required=True)

    # duplicate partner infos to keep trace of where the documents was sent
    partner_id = fields.Many2one('res.partner', 'Recipient partner', states={'sent':[('readonly', True)]})
    partner_name = fields.Char('Name', required=True, states={'sent':[('readonly', True)]})
    partner_street = fields.Char('Street', required=True, states={'sent':[('readonly', True)]})
    partner_street2 = fields.Char('Street2', states={'sent':[('readonly', True)]})
    partner_state_id = fields.Many2one("res.country.state", 'State', states={'sent':[('readonly', True)]})
    partner_zip = fields.Char('Zip', required=True, states={'sent':[('readonly', True)]})
    partner_city = fields.Char('City', required=True, states={'sent':[('readonly', True)]})
    partner_country_id = fields.Many2one('res.country', 'Country', required=True, states={'sent':[('readonly', True)]})


    # --------------------------------------------------
    # Actions
    # --------------------------------------------------
    @api.multi
    def action_reset_draft(self):
        self.write({
            'state' : 'draft',
            'error_message' : False
        })

    @api.multi
    def action_send_now(self):
        self.process_order_queue(self.ids)

    @api.multi
    def action_compute_price(self):
        """ Compute the price of the delivery. """
        self._prepare_printing()

        providers = set(self.mapped('provider_id.id'))
        for provider_id in providers: # process by provider id
            records = self.filtered(lambda r: r.provider_id.id == provider_id)
            # call provider implementation
            provider_name = records[0].provider_id.provider
            if hasattr(records, '_%s_action_compute_price' % provider_name):
                getattr(records, '_%s_action_compute_price' % provider_name)()


    # --------------------------------------------------
    # Business Methods
    # --------------------------------------------------

    def _count_pages_pdf(self, bin_pdf):
        """ Count the number of pages of the given pdf file.
            :param bin_pdf : binary content of the pdf file
        """
        pages = 0
        for match in re.compile(r"/Count\s+(\d+)").finditer(bin_pdf):
            pages = int(match.group(1))
        return pages

    def _generate_attachment(self):
        """ For the given recordset, compute the number of page in the attachment.
            If no attachment, one will be generated with the res_model/res_id
        """
        Attachment = self.env['ir.attachment']
        ReportXml = self.env['ir.actions.report.xml']
        Report = self.env['report']
        pages = {}
        for current_order in self:
            report = ReportXml.search([('model', '=', current_order.res_model)], limit=1)
            if current_order.attachment_id: # compute page number
                # avoid to recompute the number of page each time for the attachment
                nbr_pages = pages.get(current_order.attachment_id.id)
                if not nbr_pages:
                    nbr_pages = current_order._count_pages_pdf(current_order.attachment_id.datas.decode('base64'))
                    pages[current_order.attachment_id.id] = nbr_pages
                current_order.write({
                    'nbr_pages' : nbr_pages
                })
            elif not current_order.attachment_id and current_order.res_model and current_order.res_id and report: # check report
                # browse object and find its pdf (binary content)
                object_to_print = self.env[current_order.res_model].browse(current_order.res_id)
                bin_pdf = Report.get_pdf(object_to_print, report.report_name)

                # compute the name of the new attachment
                filename = False
                if report.attachment:
                    filename = safe_eval(report.attachment, {'object': object_to_print, 'time': time})
                if not filename:
                    filename = '%s-%s' % (current_order.res_model.replace(".", "_"), current_order.res_id)

                # create the new ir_attachment
                attachment_value = {
                    'name': filename,
                    'res_name': filename,
                    'res_model': current_order.res_model,
                    'res_id': current_order.res_id,
                    'datas': base64.b64encode(bin_pdf),
                    'datas_fname': filename+'.pdf',
                }
                new_attachment = Attachment.create(attachment_value)

                # add the new attachment to the print order
                current_order.write({
                    'nbr_pages' : self._count_pages_pdf(bin_pdf),
                    'attachment_id' : new_attachment.id
                })
            elif not current_order.attachment_id and current_order.res_model and current_order.res_id and not report: # error : no ir.actions.report.xml found for res_model
                current_order.write({
                    'state' : 'error',
                    'error_message' : _('The document you want to print and send is not printable. There is no report action (ir.actions.report.xml) for the model %s.') % (current_order.res_model,)
                })
            else: # error : not attachament can be generate, no attach_id or no res_model/res_id
                current_order.write({
                    'state' : 'error',
                    'error_message' : _('The document has no associated PDF : you have to give select an Attachment file, or set up the Object ID and Model Name fields.')
                })

    def _prepare_printing(self):
        """ Prepare the orders for delivery. It executes the operations to put
            them into the 'ready' state (or 'error' if something wrong happens).
            To allow optimizations in the provider implementation, the orders
            are grouped by provider.
        """
        # generate PDF for the recordset
        self._generate_attachment()

        providers = set(self.mapped('provider_id.id'))
        for provider_id in providers: # process by provider id
            records = self.filtered(lambda r: r.provider_id.id == provider_id)
            # call provider implementation
            provider_name = records[0].provider_id.provider
            if hasattr(records, '_%s_prepare_printing' % provider_name):
                getattr(records, '_%s_prepare_printing' % provider_name)()

    def _deliver_printing(self):
        """ Send the orders for delivery to the Provider. It executes the operations to put
            them into the 'sent' state (or 'error' if something wrong happens).
            Required : the print.order must be in the 'ready' state.
            This method group print.order by provider (type), to stay the optimized.
        """
        providers = set(self.mapped('provider_id.provider'))
        for provider_name in providers: # process by provider type
            if hasattr(self, '_%s_deliver_printing' % provider_name):
                records = self.filtered(lambda r: r.provider_id.provider == provider_name)
                getattr(records, '_%s_deliver_printing' % provider_name)()

    def _validate_printing(self):
        """ For the given recordset, apply the action on the printable objects when the sending
            is correctly done. This call the 'print_validate_sending' method of the printable
            object (see print.mixin below).
            This method group the PO by res_model to optimize the browse.
        """
        # group the PO by res_model
        for model in set(self.mapped('res_model')):
            if hasattr(self.env[model], 'print_validate_sending'):
                objects = self.env[model].browse(self.filtered(lambda r: r.res_model == model).mapped('res_id'))
                objects.print_validate_sending()

    @api.model
    def process_order_queue(self, order_ids=None):
        """ Immediately send the queue, or the list of given order_ids.
            If the sending failed, it send a mail_message to the author of the print order, and the PO state
            is set to 'error'. If sending is successful, the state will be 'sent'.
            This method is called by the sendnow wizard, but also by the ir_cron.
            :param order_ids : optinal list of order ids
        """
        # find ids if not given, and only keep the not sent orders
        if not order_ids:
            orders = self.search([('state', 'not in', ['sent'])])
        else:
            orders = self.browse(order_ids).filtered(lambda r: not r.state in ['sent'])

        # prepare all the orders
        orders._prepare_printing()
        # deliver only the 'ready' ones
        orders.filtered(lambda r: r.state == 'ready')._deliver_printing()
        # validate the sending, only on the correctly sent
        orders.filtered(lambda r: r.state == 'sent')._validate_printing()

        # error control : built the list of user to notify
        # create a dict 'user_to_notify' where
        #   key = user_id
        #   value = list of tuple (order_id, error_message) for all order not sent correctly
        user_to_notify = {}
        for record in orders.filtered(lambda record: record.state == 'error'):
            user_to_notify.setdefault(record.user_id.id, list()).append((record.id, record.error_message))

        # send a message to the author of the failed print orders
        template = self.env['ir.model.data'].xmlid_to_object('print.print_user_notify_failed_email_template')
        for user_id in user_to_notify.keys():
            template.with_context(print_errors=user_to_notify[user_id]).send_mail(user_id, force_send=True)



class PrintMixin(models.AbstractModel):
    """ All printable object must inherit of the class. It provides :
        - a fields 'print_sent_date' containing the datetime of the last time a print order
          for the current object was correctly deliver
        - a method 'print_validate_sending', called when the sending was successful. Therefore, 'print_sent_date'
          is set, and if this method is override, the object can have a custom behavior to apply in case of successful
          (e.i. : changing state, ...)
    """

    _name = 'print.mixin'
    _description = "Print Mixin (Printable Object)"

    print_sent_date = fields.Datetime("Last Postal Sent Date")

    def print_validate_sending(self):
        # save sending date
        self.write({
            'print_sent_date' : fields.Datetime.now()
        })

