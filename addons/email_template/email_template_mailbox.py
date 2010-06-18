from osv import osv, fields
import time
import email_template_engines
import netsvc
from tools.translate import _
import tools

LOGGER = netsvc.Logger()

class email_template_mailbox(osv.osv):
    _name = "email_template.mailbox"
    _description = 'Email Mailbox'
    _rec_name = "subject"
    _order = "date_mail desc"
    
    def run_mail_scheduler(self, cursor, user, context=None):
        """
        This method is called by Open ERP Scheduler
        to periodically send emails
        """
        try:
            self.send_all_mail(cursor, user, context)
        except Exception, e:
            LOGGER.notifyChannel(
                                 _("Email Template"),
                                 netsvc.LOG_ERROR,
                                 _("Error sending mail: %s" % str(e)))
        
    def send_all_mail(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
        if 'filters' in context.keys():
            for each_filter in context['filters']:
                filters.append(each_filter)
        ids = self.search(cr, uid, filters, context=context)
        self.write(cr, uid, ids, {'state':'sending'}, context)
        self.send_this_mail(cr, uid, ids, context)
        return True
    
    def send_this_mail(self, cr, uid, ids=None, context=None):
        for id in (ids or []):
            try:
                account_obj = self.pool.get('email_template.account')
                values = self.read(cr, uid, id, [], context) 
                payload = {}
                if values['attachments_ids']:
                    for attid in values['attachments_ids']:
                        attachment = self.pool.get('ir.attachment').browse(cr, uid, attid, context)#,['datas_fname','datas'])
                        payload[attachment.datas_fname] = attachment.datas
                result = account_obj.send_mail(cr, uid,
                              [values['account_id'][0]],
                              {'To':values.get('email_to', u'') or u'', 'CC':values.get('email_cc', u'') or u'', 'BCC':values.get('email_bcc', u'') or u''},
                              values['subject'] or u'',
                              {'text':values.get('body_text', u'') or u'', 'html':values.get('body_html', u'') or u''},
                              payload=payload, context=context)
                
                if result == True:
                    self.write(cr, uid, id, {'folder':'sent', 'state':'na', 'date_mail':time.strftime("%Y-%m-%d %H:%M:%S")}, context)
                    self.historise(cr, uid, [id], "Email sent successfully", context)
                else:
                    self.historise(cr, uid, [id], result, context)
            except Exception, error:
                logger = netsvc.Logger()
                logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (id, error))
                self.historise(cr, uid, [id], error, context)
            self.write(cr, uid, id, {'state':'na'}, context)
        return True
    
    def historise(self, cr, uid, ids, message='', context=None):
        for id in ids:
            history = self.read(cr, uid, id, ['history'], context).get('history', '')
            self.write(cr, uid, id, {'history':history or '' + "\n" + time.strftime("%Y-%m-%d %H:%M:%S") + ": " + tools.ustr(message)}, context)
    
    _columns = {
            'email_from':fields.char(
                            'From', 
                            size=64),
            'email_to':fields.char(
                            'Recepient (To)', 
                            size=250,),
            'email_cc':fields.char(
                            ' CC', 
                            size=250),
            'email_bcc':fields.char(
                            ' BCC', 
                            size=250),
            'subject':fields.char(
                            ' Subject', 
                            size=200,),
            'body_text':fields.text(
                            'Standard Body (Text)'),
            'body_html':fields.text(
                            'Body (Text-Web Client Only)'),
            'attachments_ids':fields.many2many(
                            'ir.attachment', 
                            'mail_attachments_rel', 
                            'mail_id', 
                            'att_id', 
                            'Attachments'),
            'account_id' :fields.many2one(
                            'email_template.account',
                            'User account', 
                            required=True),
            'user':fields.related(
                            'account_id', 
                            'user', 
                            type="many2one", 
                            relation="res.users", 
                            string="User"),
            'server_ref':fields.integer(
                            'Server Reference of mail', 
                            help="Applicable for inward items only"),
            'mail_type':fields.selection([
                            ('multipart/mixed', 
                             'Has Attachments'),
                            ('multipart/alternative', 
                             'Plain Text & HTML with no attachments'),
                            ('multipart/related', 
                             'Intermixed content'),
                            ('text/plain', 
                             'Plain Text'),
                            ('text/html', 
                             'HTML Body'),
                            ], 'Mail Contents'),
            #I like GMAIL which allows putting same mail in many folders
            #Lets plan it for 0.9
            'folder':fields.selection([
                            ('drafts', 'Drafts'),
                            ('outbox', 'Outbox'),
                            ('trash', 'Trash'),
                            ('sent', 'Sent Items'),
                            ], 'Folder', required=True),
            'state':fields.selection([
                            ('na', 'Not Applicable'),
                            ('sending', 'Sending'),
                            ], 'Status', required=True),
            'date_mail':fields.datetime(
                            'Rec/Sent Date'),
            'history':fields.text(
                            'History', 
                            readonly=True, 
                            store=True)
        }

    _defaults = {
        'state': lambda * a: 'na',
        'folder': lambda * a: 'outbox',
    } 

email_template_mailbox()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
