# Run by test.sh through `odoo-bin shell` (env is the shell's environment), on a
# database installed with the base code: the picking form, as installed, must
# still render, and an Italian warehouse's delivery type must get a DDT sequence
# that follows a rename of its prefix together with its warehouse (the scenario
# of the failing test), through the method as 20.0 defines it. Each step is
# reported on one EVAL_RESULT line. The transaction is rolled back, so the check
# can run several times.
import json

result = {"error": None}


def step(name, func):
    try:
        result[name] = func()
    except Exception as e:  # noqa: BLE001 - reported to the criterion
        result[name] = False
        result[name + "_error"] = f"{type(e).__name__}: {e}"


try:
    # 1. the picking form view, with the arch the database was installed with
    step("form_view", lambda: bool(env['stock.picking'].get_view(view_type='form')['arch']))

    # 2. an Italian company: its warehouses' delivery types get a DDT sequence
    company = env['res.company'].create({'name': 'Eval Italia', 'country_id': env.ref('base.it').id})
    env = env(context=dict(env.context, allowed_company_ids=[company.id]))
    warehouse = env['stock.warehouse'].create({'name': 'Milano', 'code': 'MIL', 'company_id': company.id})
    picking_type = warehouse.out_type_id
    step("sequence_created", lambda: bool(picking_type.l10n_it_ddt_sequence_id))

    # 3. the scenario of the failing test: rename the prefix and the warehouse at once
    def rename():
        picking_type.write({'sequence_code': 'MOUT', 'warehouse_id': warehouse.id})
        seq = picking_type.l10n_it_ddt_sequence_id
        result['renamed'] = {'prefix': seq.prefix, 'name': seq.name}
        return (seq.prefix, seq.name) == ('MOUTDDT', 'Milano Sequence MOUT')
    step("rename", rename)

    # 4. the method as every caller and override on 20.0 uses it: with an id
    step("stable_signature", lambda: tuple(picking_type._get_dtt_ir_seq_vals(warehouse.id, 'MOUT')) == ('Milano Sequence MOUT', 'MOUTDDT'))
    step("stable_signature_no_warehouse", lambda: tuple(picking_type._get_dtt_ir_seq_vals(False, 'OUT')) == ('Sequence OUT', 'OUTDDT'))
except Exception as e:  # noqa: BLE001 - reported to the criterion
    result['error'] = f'{type(e).__name__}: {e}'
finally:
    env.cr.rollback()
print('EVAL_RESULT ' + json.dumps(result))
