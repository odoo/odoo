import { expect, test } from '@odoo/hoot';
import {
    models,
    fields,
    defineModels,
    mountView,
    contains,
    onRpc,
} from '@web/../tests/web_test_helpers';

class Category extends models.Model {
    name = fields.Char();
    _records = [
        { id: 1, name: 'Cat A' },
        { id: 2, name: 'Cat B' },
    ];
}

class Product extends models.Model {
    name = fields.Char();
    category_id = fields.Many2one({ 
        relation: 'category', 
    });
    _records = [
        { id: 1, name: 'A-1', category_id: 1 },
        { id: 2, name: 'A-2', category_id: 1 },
        { id: 3, name: 'B-1', category_id: 2 },
    ];
}

defineModels({ Category, Product });

onRpc('has_group', () => true);

test('expand/collapse all groups from cog menu in grouped list', async () => {
    await mountView({
        type: 'list',
        resModel: 'product',
        groupBy: ['category_id'],
        arch: `<list string='Products'><field name='name'/><field name='category_id'/></list>`,
    });
    expect('.o_group_header').toHaveCount(2);
    await contains('.o_cp_action_menus .dropdown-toggle').click();
    expect('.mk_expand_all_menu').toHaveCount(1);
    expect('.mk_collapse_all_menu').toHaveCount(1);
    await contains('.mk_expand_all_menu').click();
    expect('tbody tr.o_data_row').toHaveCount(3);
    await contains('.o_cp_action_menus .dropdown-toggle').click();
    await contains('.mk_collapse_all_menu').click();
    expect('tbody tr.o_data_row').toHaveCount(0);
    expect('.o_group_header').toHaveCount(2);
});
