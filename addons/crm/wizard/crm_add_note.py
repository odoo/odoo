from crm import crm
from osv import fields, osv
from tools.translate import _
import base64

AVAILABLE_STATES = crm.AVAILABLE_STATES + [('unchanged', 'Unchanged')]


class crm_add_note(osv.osv_memory):
    """Adds a new note to the case."""
    _name = 'crm.add.note'
    _description = "Add Internal Note"

    _columns = {
        'body': fields.text('Note Body', required=True),
        'state': fields.selection(AVAILABLE_STATES, string='Set New State To',
                                  required=True), 
        'attachment_ids' : fields.one2many('crm.send.mail.attachment', 'wizard_id'),
    }

    def action_add(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        if not context.get('active_model'):
            raise osv.except_osv(_('Error'), _('Can not add note!'))

        model = context.get('active_model')
        case_pool = self.pool.get(model)

        for obj in self.browse(cr, uid, ids, context=context):
            case_list = case_pool.browse(cr, uid, context['active_ids'],
                                         context=context)
            case = case_list[0]
            user_obj = self.pool.get('res.users')
            user_name = user_obj.browse(cr, uid, [uid], context=context)[0].name
            attach = [
                (x.name, base64.decodestring(x.binary)) for x in obj.attachment_ids
            ]
            case_pool.history(cr, uid, [case], self.pool.get('mailgate.message').truncate_data(cr, uid, obj.body, context=context), history=False,
                              details=obj.body, email_from=user_name, attach=attach)

            if obj.state == 'unchanged':
                pass
            elif obj.state == 'done':
                case_pool.case_close(cr, uid, [case.id])
            elif obj.state == 'draft':
                case_pool.case_reset(cr, uid, [case.id])
            elif obj.state in ['cancel', 'open', 'pending']:
                act = 'case_' + obj.state
                getattr(case_pool, act)(cr, uid, [case.id])

        return {'type': 'ir.actions.act_window_close'}

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        return {'state': u'unchanged'}


crm_add_note()
