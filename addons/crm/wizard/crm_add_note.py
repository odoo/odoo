from .. import crm
from osv import fields, osv
from tools.translate import _
from mail.mail_message import truncate_text

AVAILABLE_STATES = crm.AVAILABLE_STATES + [('unchanged', 'Unchanged')]

class crm_add_note(osv.osv_memory):
    """Adds a new note to the case."""
    _name = 'crm.add.note'
    _description = "Add Internal Note"

    _columns = {
        'body': fields.text('Note Body', required=True),
        'state': fields.selection(AVAILABLE_STATES, string='Set New State To',
                                  required=True),
    }

    _defaults = {
        'state': 'unchanged'
    }

    def action_add(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        if not context.get('active_model'):
            raise osv.except_osv(_('Error'), _('Cannot add note.'))

        model = context.get('active_model')
        case_pool = self.pool.get(model)

        for obj in self.browse(cr, uid, ids, context=context):
            case_list = case_pool.browse(cr, uid, context['active_ids'],
                                         context=context)
            case = case_list[0]
            case_pool.message_append(cr, uid, [case], truncate_text(obj.body),
                                     body_text=obj.body)
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

crm_add_note()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
