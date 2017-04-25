from collections import OrderedDict
import csv

import xlrd


def _e(s):
    if type(s) is unicode:
        return s.encode('utf8')
    elif s is None:
        return ''
    else:
        return str(s)


def _is_true(s):
    return s not in ('F', 'False', 0, '', None, False)


class LuxTaxGenerator:

    def __init__(self, filename):
        self.workbook = xlrd.open_workbook('tax.xls')
        self.sheet_info = \
            self.workbook.sheet_by_name('INFO')
        self.sheet_taxes = \
            self.workbook.sheet_by_name('TAXES')
        self.sheet_tax_codes = \
            self.workbook.sheet_by_name('TAX.CODES')
        self.sheet_fiscal_pos_map = \
            self.workbook.sheet_by_name('FISCAL.POSITION.MAPPINGS')
        self.suffix = self.sheet_info.cell_value(4, 2)

    def iter_tax_codes(self):
        keys = map(lambda c: c.value, self.sheet_tax_codes.row(0))
        yield keys
        for i in range(1, self.sheet_tax_codes.nrows):
            row = map(lambda c: c.value, self.sheet_tax_codes.row(i))
            d =  OrderedDict(zip(keys, row))
            d['sign'] = int(d['sign'])
            d['sequence'] = int(d['sequence'])
            yield d

    def iter_taxes(self):
        keys = map(lambda c: c.value, self.sheet_taxes.row(0))
        yield keys
        for i in range(1, self.sheet_taxes.nrows):
            row = map(lambda c: c.value, self.sheet_taxes.row(i))
            yield OrderedDict(zip(keys, row))

    def iter_fiscal_pos_map(self):
        keys = map(lambda c: c.value, self.sheet_fiscal_pos_map.row(0))
        yield keys
        for i in range(1, self.sheet_fiscal_pos_map.nrows):
            row = map(lambda c: c.value, self.sheet_fiscal_pos_map.row(i))
            yield OrderedDict(zip(keys, row))

    def tax_codes_to_csv(self):
        writer = csv.writer(open('account.tax.code.template-%s.csv' %
                                 self.suffix, 'wb'))
        tax_codes_iterator = self.iter_tax_codes()
        keys = next(tax_codes_iterator)
        writer.writerow(keys)

        # write structure tax codes
        tax_codes = {}  # code: id
        for row in tax_codes_iterator:
            tax_code = row['code']
            if tax_code in tax_codes:
                raise RuntimeError('duplicate tax code %s' % tax_code)
            tax_codes[tax_code] = row['id']
            writer.writerow(map(_e, row.values()))

        # read taxes and add leaf tax codes
        new_tax_codes = {}  # id: parent_code

        def add_new_tax_code(tax_code_id, new_name, new_parent_code):
            if not tax_code_id:
                return
            name, parent_code = new_tax_codes.get(tax_code_id, (None, None))
            if parent_code and parent_code != new_parent_code:
                raise RuntimeError('tax code "%s" already exist with '
                                   'parent %s while trying to add it with '
                                   'parent %s' %
                                   (tax_code_id, parent_code, new_parent_code))
            else:
                new_tax_codes[tax_code_id] = (new_name, new_parent_code)

        taxes_iterator = self.iter_taxes()
        next(taxes_iterator)
        for row in taxes_iterator:
            if not _is_true(row['active']):
                continue
            if row['child_depend'] and row['amount'] != 1:
                raise RuntimeError('amount must be one if child_depend '
                                   'for %s' % row['id'])
            # base parent
            base_code = row['BASE_CODE']
            if not base_code or base_code == '/':
                base_code = 'NA'
            if base_code not in tax_codes:
                raise RuntimeError('undefined tax code %s' % base_code)
            if base_code != 'NA':
                if row['child_depend']:
                    raise RuntimeError('base code specified '
                                       'with child_depend for %s' % row['id'])
            if not row['child_depend']:
                # ... in lux, we have the same code for invoice and refund
                if base_code != 'NA':
                    assert row['base_code_id:id'], 'missing base_code_id for %s' % row['id']
                assert row['ref_base_code_id:id'] == row['base_code_id:id']
                add_new_tax_code(row['base_code_id:id'],
                                 'Base - ' + row['name'],
                                 base_code)
            # tax parent
            tax_code = row['TAX_CODE']
            if not tax_code or tax_code == '/':
                tax_code = 'NA'
            if tax_code not in tax_codes:
                raise RuntimeError('undefined tax code %s' % tax_code)
            if tax_code == 'NA':
                if row['amount'] and not row['child_depend']:
                    raise RuntimeError('TAX_CODE not specified '
                                       'for non-zero tax %s' % row['id'])
                if row['tax_code_id:id']:
                    raise RuntimeError('tax_code_id specified '
                                       'for tax %s' % row['id'])
            else:
                if row['child_depend']:
                    raise RuntimeError('TAX_CODE specified '
                                       'with child_depend for %s' % row['id'])
                if not row['amount']:
                    raise RuntimeError('TAX_CODE specified '
                                       'for zero tax %s' % row['id'])
                if not row['tax_code_id:id']:
                    raise RuntimeError('tax_code_id not specified '
                                       'for tax %s' % row['id'])
            if not row['child_depend'] and row['amount']:
                # ... in lux, we have the same code for invoice and refund
                assert row['tax_code_id:id'], 'missing tax_code_id for %s' % row['id']
                assert row['ref_tax_code_id:id'] == row['tax_code_id:id']
                add_new_tax_code(row['tax_code_id:id'],
                                 'Taxe - ' + row['name'],
                                 tax_code)

        for tax_code_id in sorted(new_tax_codes):
            name, parent_code = new_tax_codes[tax_code_id]
            writer.writerow((tax_code_id,
                             'lu_tct_m' + parent_code,
                             tax_code_id.replace('lu_tax_code_template_', ''),
                             '1',
                             '',
                             _e(name),
                             ''))

    def taxes_to_csv(self):
        writer = csv.writer(open('account.tax.template-%s.csv' %
                                 self.suffix, 'wb'))
        taxes_iterator = self.iter_taxes()
        keys = next(taxes_iterator)
        writer.writerow(keys[3:] + ['sequence'])
        seq = 100
        for row in sorted(taxes_iterator, key=lambda r: r['description']):
            if not _is_true(row['active']):
                continue
            seq += 1
            if row['parent_id:id']:
                cur_seq = seq + 1000
            else:
                cur_seq = seq
            writer.writerow(map(_e, row.values()[3:]) + [cur_seq])

    def fiscal_pos_map_to_csv(self):
        writer = csv.writer(open('account.fiscal.'
                                 'position.tax.template-%s.csv' %
                                 self.suffix, 'wb'))
        fiscal_pos_map_iterator = self.iter_fiscal_pos_map()
        keys = next(fiscal_pos_map_iterator)
        writer.writerow(keys)
        for row in fiscal_pos_map_iterator:
            writer.writerow(map(_e, row.values()))


if __name__ == '__main__':
    o = LuxTaxGenerator('tax.xls')
    o.tax_codes_to_csv()
    o.taxes_to_csv()
    o.fiscal_pos_map_to_csv()
