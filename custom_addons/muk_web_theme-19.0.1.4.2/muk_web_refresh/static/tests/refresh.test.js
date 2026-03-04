import { expect, test } from '@odoo/hoot';
import { click, dblclick } from '@odoo/hoot-dom';
import { advanceTime, animationFrame } from '@odoo/hoot-mock';

import { defineMailModels } from '@mail/../tests/mail_test_helpers';

import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from '@web/../tests/web_test_helpers';

import '@muk_web_refresh/search/control_panel';

class Product extends models.Model {
    _records = [
        { id: 1, name: 'Test 1' },
        { id: 2, name: 'Test 2' },
    ];
    name = fields.Char();
}

defineModels([Product]);
defineMailModels();

test.tags('muk_web_refresh');
test('refresh button is visible on list view', async () => {
    onRpc('has_group', () => true);
    await mountView({
        type: 'list',
        resModel: 'product',
        arch: `<list><field name="name"/></list>`,
    });
    expect('.o_cp_refresh .fa-refresh').toHaveCount(1);
});

test.tags('muk_web_refresh');
test('refresh button is visible on kanban view', async () => {
    onRpc('has_group', () => true);
    await mountView({
        type: 'kanban',
        resModel: 'product',
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    expect('.o_cp_refresh .fa-refresh').toHaveCount(1);
});

test.tags('muk_web_refresh');
test('refresh button is visible on form view', async () => {
    onRpc('has_group', () => true);
    await mountView({
        type: 'form',
        resModel: 'product',
        resId: 1,
        arch: `<form><field name="name"/></form>`,
    });
    expect('.o_cp_refresh .fa-refresh').toHaveCount(1);
});

test.tags('muk_web_refresh');
test('single click triggers refresh', async () => {
    onRpc('has_group', () => true);
    await mountView({
        type: 'list',
        resModel: 'product',
        arch: `<list><field name="name"/></list>`,
    });
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-muted');
    await click('.o_cp_refresh .fa-refresh');
    await advanceTime(350);
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-muted');
});

test.tags('muk_web_refresh');
test('double click toggles auto refresh on list view', async () => {
    onRpc('has_group', () => true);
    await mountView({
        type: 'list',
        resModel: 'product',
        arch: `<list><field name="name"/></list>`,
    });
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-muted');
    await dblclick('.o_cp_refresh .fa-refresh');
    await animationFrame();
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-info');
    expect('.o_cp_refresh .fa-refresh').not.toHaveClass('text-muted');
    await dblclick('.o_cp_refresh .fa-refresh');
    await animationFrame();
    expect('.o_cp_refresh .fa-refresh').not.toHaveClass('text-info');
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-muted');
});

test.tags('muk_web_refresh');
test('double click does not toggle auto refresh on form view', async () => {
    onRpc('has_group', () => true);
    await mountView({
        type: 'form',
        resModel: 'product',
        resId: 1,
        arch: `<form><field name="name"/></form>`,
    });
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-muted');
    await dblclick('.o_cp_refresh .fa-refresh');
    await animationFrame();
    expect('.o_cp_refresh .fa-refresh').toHaveClass('text-muted');
});
