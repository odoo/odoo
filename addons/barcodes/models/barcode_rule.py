import logging
import re


from openerp import tools, models, fields, api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class barcode_rule(models.Model):
    _name = 'barcode.rule'
    _order = 'sequence asc'

    @api.model
    def _encoding_selection_list(self):
        return [
                ('any', 'Any'),
                ('ean13', 'EAN-13'),
                ('ean8', 'EAN-8'),
                ('upca', 'UPC-A'),
        ]

    @api.model
    def _get_type_selection(self):
        return [('alias','Alias'),('product','Unit Product')]

    _columns = {
        'name':     fields.char('Rule Name', size=32, required=True, help='An internal identification for this barcode nomenclature rule'),
        'barcode_nomenclature_id':     fields.many2one('barcode.nomenclature','Barcode Nomenclature'),
        'sequence': fields.integer('Sequence', help='Used to order rules such that rules with a smaller sequence match first'),
        'encoding': fields.selection('_encoding_selection_list','Encoding',required=True,help='This rule will apply only if the barcode is encoded with the specified encoding'),
        'type':     fields.selection('_get_type_selection','Type', required=True),
        'pattern':  fields.char('Barcode Pattern', size=32, help="The barcode matching pattern", required=True),
        'alias':    fields.char('Alias',size=32,help='The matched pattern will alias to this barcode', required=True),      
    }

    _defaults = {
        'type': 'product',
        'pattern': '.*',
        'encoding': 'any',
        'alias': "0",
    }

    @api.one
    @api.constrains('pattern')
    def _check_pattern(self):
        p = self.pattern.replace("\\\\", "X").replace("\{", "X").replace("\}", "X")
        findall = re.findall("[{]|[}]", p) # p does not contain escaped { or }
        if len(findall) == 2: 
            if not re.search("[{][N]*[D]*[}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": braces can only contain N's followed by D's."))
            elif re.search("[{][}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": empty braces."))
        elif len(findall) != 0:
            raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": a rule can only contain one pair of braces."))
        elif p == '*':
            raise ValidationError(_(" '*' is not a valid Regex Barcode Pattern. Did you mean '.*' ?"))

        
