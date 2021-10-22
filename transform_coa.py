import xml.etree.ElementTree as ET
import os
import glob
from collections import defaultdict
class create:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Command.create({ppformat(self.value)})"

class clear:
    def __repr__(self):
        return f"Command.clear()"

class ref:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"ref({f_ise(self.value)}).id"

class company_ref(ref):
    def __init__(self, value):
        self.value = value.split('.')[-1]

    def __repr__(self):
        return f"ref({f_ise('account.{cid}_' + self.value)}).id"

class o2m:
    def __init__(self, model=None):
        self.__model = model

    def __call__(self, value):
        value = eval(value)
        for i, item in enumerate(list(value)):
            if isinstance(item, (tuple, list)):
                if item[0] == 0:
                    vals = item[2]
                    if self.__model:
                        for f, v in vals.items():
                            if models[self.__model].get(f) is company_ref:
                                vals[f] = company_ref(vals[f].value)
                    value[i] = create(vals)
                if item[0] == 5:
                    value[i] = clear()
        self.value = value
        return self

    def __repr__(self):
        return ppformat(self.value)

delete = object()

def f_ise(k):
    return f"{'f' if 'cid' in k else ''}'{k}'"

def ppformat(o, level=0):
    raw = o.value if isinstance(o, (o2m, create)) else o
    if isinstance(o, (tuple, list, dict, create, o2m)):
        if isinstance(o, (tuple, list, o2m)):
            if   isinstance(o, tuple): start, end = "()"
            elif isinstance(o, list):  start, end = "[]"
            elif isinstance(o, o2m):   start, end = "[]"
            content = [ppformat(e, level+1) for e in raw]
        if isinstance(o, (dict, create)):
            if   isinstance(o, dict):   start, end = "{}"
            elif isinstance(o, create): start, end = "Command.create({", "})"
            content = [f"{f_ise(k)}: {ppformat(v, level+1)}" for k, v in raw.items()]
        return f"{start}\n{'    ' * (level + 1)}{('    ' * (level + 1)).join(content)}{'    ' * level}{end},\n"
    elif isinstance(o, (clear, ref, str, int, float, bool)):
        return repr(o) + (',\n' if level else '')
    raise ValueError((o, type(o)))

def ppprint(o):
    print(ppformat(o))

models = {
    'account.tax.template': {
        'name': str,
        'amount': float,
        'active': bool,
        'chart_template_id': delete,
        'description': str,
        'price_include': bool,
        'sequence': int,
        'tax_group_id': company_ref,
        'amount_type': str,
        'type_tax_use': str,
        'tax_discount': bool,
        'python_compute': str,
        'tax_exigibility': str,
        'invoice_repartition_line_ids': o2m('account.tax.repartition.line'),
        'refund_repartition_line_ids': o2m('account.tax.repartition.line'),
        'cash_basis_transition_account_id': company_ref,
        'include_base_amount': bool,
        'children_tax_ids': o2m('account.tax.template'),
        'l10n_pe_edi_tax_code': str,
        'l10n_pe_edi_unece_category': ref,
        'l10n_cl_sii_code': str,
        'l10n_de_datev_code': str,
    },
    'account.tax.repartition.line': {
        'factor_percent': float,
        'repartition_type': str,
        'account_id': company_ref,
        'minus_report_line_ids': o2m(),
        'plus_report_line_ids': o2m(),
    }
}
root_path = os.path.dirname(os.path.realpath(__file__))
for file in (
    glob.glob(root_path + '/**/l10n_be*/**/*.xml', recursive=True)
    # + glob.glob(root_path + '/../enterprise/**/*.xml', recursive=True)
):
    try:
        tree = ET.parse(file)
    except ET.ParseError:
        continue

    root = tree.getroot()
    if not any(
        root.find(f'.//record[@model="{model}"]') is not None
        for model in models
    ):
        continue

    print(file)
    for model, fields in models.items():
        data = defaultdict(dict)
        for record in root.findall(f'.//record[@model="{model}"]'):
            for field in record.findall('field'):
                parse = fields.get(field.get('name'))
                if parse == delete:
                    continue
                if parse is None:
                    # raise ValueError('not taken in charge', model, field.get('name'))
                    continue
                if field.get('search'):
                    raise ValueError('prout', model, field.get('name'), field.get('search'))
                value = parse(field.text or field.get('eval') or field.get('ref'))
                data[f"{{cid}}_{record.get('id')}"][field.get('name')] = value
        if data:
            print(model)
            ppprint(data)
