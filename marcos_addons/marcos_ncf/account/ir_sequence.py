# -*- encoding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _

class ir_sequence(osv.Model):
    _inherit = 'ir.sequence'

    _columns = {
        'ncf_limit': fields.integer(u"NCF solicitados", help=u"Si la esta secuencia corresponde a Números de comprobantes fiscales debe especificar la cantidad de NCF solicitada, para recibir una notificación cuando estén apunto de agotarse"),
        'user_id': fields.many2one('res.users', u'NCF Responsable', help=u'Debe especificar la persona resposable de de solicitar los NCF para que reciba una notificacion cuando estos se esten agotando.'),
        'ncf_notify': fields.integer(u"Notificación de NCF", help=u"Cuando la cantidad de secuencias de NCF restantes sean menor o igual al valor de este campo, se notificará para solicitar más."),
    }

    _defaults = {
        'ncf_notify' : 250,
        }

    def _next(self, cr, uid, seq_ids, context=None):
        if not seq_ids:
            return False
        if context is None:
            context = {}
        force_company = context.get('force_company')
        if not force_company:
            force_company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        sequences = self.read(cr, uid, seq_ids, ['name','company_id','implementation','number_next','prefix','suffix','padding', 'ncf_limit'])
        preferred_sequences = [s for s in sequences if s['company_id'] and s['company_id'][0] == force_company ]
        seq = preferred_sequences[0] if preferred_sequences else sequences[0]
        if seq['implementation'] == 'standard':
            cr.execute("SELECT nextval('ir_sequence_%03d')" % seq['id'])
            seq['number_next'] = cr.fetchone()
        else:
            cr.execute("SELECT number_next FROM ir_sequence WHERE id=%s FOR UPDATE NOWAIT", (seq['id'],))
            cr.execute("UPDATE ir_sequence SET number_next=number_next+number_increment WHERE id=%s ", (seq['id'],))
        d = self._interpolation_dict()
        try:
            interpolated_prefix = self._interpolate(seq['prefix'], d)
            interpolated_suffix = self._interpolate(seq['suffix'], d)
        except ValueError:
            raise osv.except_osv(_('Warning'), _('Invalid prefix or suffix for sequence \'%s\'') % (seq.get('name')))

        return interpolated_prefix + '%%0%sd' % seq['padding'] % seq['number_next'] + interpolated_suffix
