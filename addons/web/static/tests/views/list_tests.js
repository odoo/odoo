odoo.define('web.list_tests', function (require) {
"use strict";

var AbstractFieldOwl = require('web.AbstractFieldOwl');
var AbstractStorageService = require('web.AbstractStorageService');
var BasicModel = require('web.BasicModel');
var core = require('web.core');
const Domain = require('web.Domain')
var basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');
var fieldRegistryOwl = require('web.field_registry_owl');
var FormView = require('web.FormView');
var ListRenderer = require('web.ListRenderer');
var ListView = require('web.ListView');
var mixins = require('web.mixins');
var NotificationService = require('web.NotificationService');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');
var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');


var _t = core._t;
const cpHelpers = testUtils.controlPanel;
var createActionManager = testUtils.createActionManager;
var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    date: {string: "Some Date", type: "date"},
                    int_field: {string: "int_field", type: "integer", sortable: true, group_operator: "sum"},
                    text: {string: "text field", type: "text"},
                    qux: {string: "my float", type: "float"},
                    m2o: {string: "M2O field", type: "many2one", relation: "bar"},
                    o2m: {string: "O2M field", type: "one2many", relation: "bar"},
                    m2m: {string: "M2M field", type: "many2many", relation: "bar"},
                    amount: {string: "Monetary field", type: "monetary"},
                    currency_id: {string: "Currency", type: "many2one",
                                  relation: "res_currency", default: 1},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                    reference: {string: "Reference Field", type: 'reference', selection: [
                        ["bar", "Bar"], ["res_currency", "Currency"], ["event", "Event"]]},
                },
                records: [
                    {
                        id: 1,
                        bar: true,
                        foo: "yop",
                        int_field: 10,
                        qux: 0.4,
                        m2o: 1,
                        m2m: [1, 2],
                        amount: 1200,
                        currency_id: 2,
                        date: "2017-01-25",
                        datetime: "2016-12-12 10:55:05",
                        reference: 'bar,1',
                    },
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13,
                     m2o: 2, m2m: [1, 2, 3], amount: 500, reference: 'res_currency,1'},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3,
                     m2o: 1, m2m: [], amount: 300, reference: 'res_currency,2'},
                    {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9,
                     m2o: 1, m2m: [1], amount: 0},
                ]
            },
            bar: {
                fields: {},
                records: [
                    {id: 1, display_name: "Value 1"},
                    {id: 2, display_name: "Value 2"},
                    {id: 3, display_name: "Value 3"},
                ]
            },
            res_currency: {
                fields: {
                    symbol: {string: "Symbol", type: "char"},
                    position: {
                        string: "Position",
                        type: "selection",
                        selection: [['after', 'A'], ['before', 'B']],
                    },
                },
                records: [
                    {id: 1, display_name: "USD", symbol: '$', position: 'before'},
                    {id: 2, display_name: "EUR", symbol: '€', position: 'after'},
                ],
            },
            event: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "name", type: "char"},
                },
                records: [
                    {id: "2-20170808020000", name: "virtual"},
                ]
            },
            "ir.translation": {
                fields: {
                    lang_code: {type: "char"},
                    src: {type: "char"},
                    value: {type: "char"},
                    res_id: {type: "integer"},
                    name: {type: "char"},
                    lang: {type: "char"},
                },
                records: [{
                    id: 99,
                    res_id: 1,
                    value: '',
                    lang_code: 'en_US',
                    lang: 'en_US',
                    name: 'foo,foo'
                },{
                    id: 100,
                    res_id: 1,
                    value: '',
                    lang_code: 'fr_BE',
                    lang: 'fr_BE',
                    name: 'foo,foo'
                }]
            },
        };
    }
}, function () {

    QUnit.module('ListView');

    QUnit.test('simple readonly list', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.doesNotHaveClass(list.$el, 'o_cannot_create',
            "should not have className 'o_cannot_create'");

        // 3 th (1 for checkbox, 2 for columns)
        assert.containsN(list, 'th', 3, "should have 3 columns");

        assert.strictEqual(list.$('td:contains(gnap)').length, 1, "should contain gnap");
        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        assert.containsOnce(list, 'th.o_column_sortable', "should have 1 sortable column");

        assert.strictEqual(list.$('thead th:nth(2)').css('text-align'), 'right',
            "header cells of integer fields should be right aligned");
        assert.strictEqual(list.$('tbody tr:first td:nth(2)').css('text-align'), 'right',
            "integer cells should be right aligned");

        assert.isVisible(list.$buttons.find('.o_list_button_add'));
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'));
        assert.isNotVisible(list.$buttons.find('.o_list_button_discard'));
        list.destroy();
    });

    QUnit.test('on_attach_callback is properly called', async function (assert) {
        assert.expect(3);

        testUtils.mock.patch(ListRenderer, {
            on_attach_callback() {
                assert.step('on_attach_callback');
                this._super(...arguments);
            },
        });

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="display_name"/></tree>',
        });

        assert.verifySteps(['on_attach_callback']);
        await list.reload();
        assert.verifySteps([]);

        testUtils.mock.unpatch(ListRenderer);
        list.destroy();
    });

    QUnit.test('list with create="0"', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree create="0"><field name="foo"/></tree>',
        });

        assert.hasClass(list.$el,'o_cannot_create',
            "should have className 'o_cannot_create'");
        assert.containsNone(list.$buttons, '.o_list_button_add',
            "should not have the 'Create' button");

        list.destroy();
    });

    QUnit.test('list with delete="0"', async function (assert) {
        assert.expect(3);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasActionMenus: true},
            arch: '<tree delete="0"><field name="foo"/></tree>',
        });


        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));
        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus .o_dropdown_menu');

        list.destroy();
    });

    QUnit.test('editable list with edit="0"', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasActionMenus: true},
            arch: '<tree editable="top" edit="0"><field name="foo"/></tree>',
        });

        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');

        await testUtils.dom.click(list.$('tr td:not(.o_list_record_selector)').first());
        assert.containsNone(list, 'tbody tr.o_selected_row', "should not have editable row");

        list.destroy();
    });

    QUnit.test('export feature in list for users not in base.group_allow_export', async function (assert) {
        assert.expect(5);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: { hasActionMenus: true },
            arch: '<tree><field name="foo"/></tree>',
            session: {
                async user_has_group(group) {
                    if (group === 'base.group_allow_export') {
                        return false;
                    }
                    return this._super(...arguments);
                },
            },
        });

        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');
        assert.containsNone(list.el, 'div.o_control_panel .o_cp_buttons .o_list_export_xlsx');

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));
        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');
        await cpHelpers.toggleActionMenu(list);
        assert.deepEqual(cpHelpers.getMenuItemTexts(list), ['Delete'],
            'action menu should not contain the Export button');

        list.destroy();
    });

    QUnit.test('list with export button', async function (assert) {
        assert.expect(5);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasActionMenus: true},
            arch: '<tree><field name="foo"/></tree>',
            session: {
                async user_has_group(group) {
                    if (group === 'base.group_allow_export') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            },
        });

        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');
        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_buttons .o_list_export_xlsx');

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));
        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');
        await cpHelpers.toggleActionMenu(list);
        assert.deepEqual(
            cpHelpers.getMenuItemTexts(list),
            ['Export', 'Delete'],
            'action menu should have Export button'
        );

        list.destroy();
    });

    QUnit.test('export button in list view', async function (assert) {
        assert.expect(5);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            session: {
                async user_has_group(group) {
                    if (group === 'base.group_allow_export') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            },
        });

        assert.containsN(list, '.o_data_row', 4);
        assert.isVisible(list.$('.o_list_export_xlsx'));

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.isNotVisible(list.$('.o_list_export_xlsx'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));
        assert.isVisible(list.$('.o_list_export_xlsx'));

        list.destroy();
    });

    QUnit.test('export button in empty list view', async function (assert) {
        assert.expect(2);

        const list = await createView({
            View: ListView,
            model: "foo",
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            domain: [["id", "<", 0]], // such that no record matches the domain
            session: {
                async user_has_group(group) {
                    if (group === 'base.group_allow_export') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            },
        });

        assert.isNotVisible(list.el.querySelector('.o_list_export_xlsx'));

        await list.reload({ domain: [['id', '>', 0]] });
        assert.isVisible(list.el.querySelector('.o_list_export_xlsx'));

        list.destroy();
    });

    QUnit.test('list view with adjacent buttons', async function (assert) {
        assert.expect(2);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
        });

        assert.containsN(list, 'th', 4,
            "adjacent buttons in the arch must be grouped in a single column");
        assert.containsN(list.$('.o_data_row:first'), 'td.o_list_button', 2);

        list.destroy();
    });

    QUnit.test('list view with adjacent buttons and invisible field', async function (assert) {
        assert.expect(2);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" invisible="1"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
        });

        assert.containsN(list, 'th', 3,
            "adjacent buttons in the arch must be grouped in a single column");
        assert.containsN(list.$('.o_data_row:first'), 'td.o_list_button', 2);

        list.destroy();
    });

    QUnit.test('list view with adjacent buttons and invisible field (modifier)', async function (assert) {
        assert.expect(2);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" attrs="{'invisible': [['foo', '=', 'blip']]}"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
        });

        assert.containsN(list, 'th', 4,
            "adjacent buttons in the arch must be grouped in a single column");
        assert.containsN(list.$('.o_data_row:first'), 'td.o_list_button', 2);

        list.destroy();
    });

    QUnit.test('list view with adjacent buttons and optional field', async function (assert) {
        assert.expect(2);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" optional="hide"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
        });

        assert.containsN(list, 'th', 3,
            "adjacent buttons in the arch must be grouped in a single column");
        assert.containsN(list.$('.o_data_row:first'), 'td.o_list_button', 2);

        list.destroy();
    });

    QUnit.test('list view with adjacent buttons with invisible modifier', async function (assert) {
        assert.expect(6);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <button name="x" type="object" icon="fa-star" attrs="{'invisible': [['foo', '=', 'blip']]}"/>
                    <button name="y" type="object" icon="fa-refresh" attrs="{'invisible': [['foo', '=', 'yop']]}"/>
                    <button name="z" type="object" icon="fa-exclamation" attrs="{'invisible': [['foo', '=', 'gnap']]}"/>
                </tree>`,
        });

        assert.containsN(list, 'th', 3,
            "adjacent buttons in the arch must be grouped in a single column");
        assert.containsOnce(list.$('.o_data_row:first'), 'td.o_list_button');
        assert.strictEqual(list.$('.o_field_cell').text(), 'yopblipgnapblip');
        assert.containsN(list, 'td button i.fa-star:visible', 2);
        assert.containsN(list, 'td button i.fa-refresh:visible', 3);
        assert.containsN(list, 'td button i.fa-exclamation:visible', 3);

        list.destroy();
    });

    QUnit.test('list view with icon buttons', async function (assert) {
        assert.expect(5);

        this.data.foo.records.splice(1);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <button name="x" type="object" icon="fa-asterisk"/>
                    <button name="x" type="object" icon="fa-star" class="o_yeah"/>
                    <button name="x" type="object" icon="fa-refresh" string="Refresh" class="o_yeah"/>
                    <button name="x" type="object" icon="fa-exclamation" string="Danger" class="o_yeah btn-danger"/>
                </tree>`,
        });

        assert.containsOnce(list, 'button.btn.btn-link i.fa.fa-asterisk');
        assert.containsOnce(list, 'button.btn.btn-link.o_yeah i.fa.fa-star');
        assert.containsOnce(list, 'button.btn.btn-link.o_yeah:contains("Refresh") i.fa.fa-refresh');
        assert.containsOnce(list, 'button.btn.btn-danger.o_yeah:contains("Danger") i.fa.fa-exclamation');
        assert.containsNone(list, 'button.btn.btn-link.btn-danger');

        list.destroy();
    });

    QUnit.test('list view: action button in controlPanel basic rendering', async function (assert) {
        assert.expect(11);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf"/>
                         <button name="y" type="object" class="plouf" string="plouf" invisible="not context.get('bim')"/>
                    </header>
                    <field name="foo" />
                </tree>`,
        });
        let cpButtons = cpHelpers.getButtons(list);
        assert.containsNone(cpButtons[0], 'button[name="x"]');
        assert.containsNone(cpButtons[0], '.o_list_selection_box');
        assert.containsNone(cpButtons[0], 'button[name="y"]');

        await testUtils.dom.click(
            list.el.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        cpButtons = cpHelpers.getButtons(list);
        assert.containsOnce(cpButtons[0], 'button[name="x"]');
        assert.hasClass(cpButtons[0].querySelector('button[name="x"]'), 'btn btn-secondary');
        assert.containsOnce(cpButtons[0], '.o_list_selection_box');
        assert.strictEqual(
            cpButtons[0].querySelector('button[name="x"]').previousElementSibling,
            cpButtons[0].querySelector('.o_list_selection_box')
        );
        assert.containsNone(cpButtons[0], 'button[name="y"]');

        await testUtils.dom.click(
            list.el.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        cpButtons = cpHelpers.getButtons(list);
        assert.containsNone(cpButtons[0], 'button[name="x"]');
        assert.containsNone(cpButtons[0], '.o_list_selection_box');
        assert.containsNone(cpButtons[0], 'button[name="y"]');

        list.destroy();
    });

    QUnit.test('list view: action button executes action on click: buttons are disabled and re-enabled', async function (assert) {
        assert.expect(3);

        const executeActionDef = testUtils.makeTestPromise();
        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf"/>
                    </header>
                    <field name="foo" />
                </tree>`,
            intercepts: {
                async execute_action(ev) {
                    const { on_success } = ev.data;
                    await executeActionDef;
                    on_success();
                }
            }
        });
        await testUtils.dom.click(
            list.el.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        const cpButtons = cpHelpers.getButtons(list);
        assert.ok(
            Array.from(cpButtons[0].querySelectorAll('button')).every(btn => !btn.disabled)
        );

        await testUtils.dom.click(cpButtons[0].querySelector('button[name="x"]'));
        assert.ok(
            Array.from(cpButtons[0].querySelectorAll('button')).every(btn => btn.disabled)
        );

        executeActionDef.resolve();
        await testUtils.nextTick();
        assert.ok(
            Array.from(cpButtons[0].querySelectorAll('button')).every(btn => !btn.disabled)
        );

        list.destroy();
    });

    QUnit.test('list view: action button executes action on click: correct parameters', async function (assert) {
        assert.expect(4);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf" context="{'plouf': 'plif'}"/>
                    </header>
                    <field name="foo" />
                </tree>`,
            intercepts: {
                async execute_action(ev) {
                    const {
                        action_data: {
                            context, name, type
                        },
                        env,
                    } = ev.data;
                    // Action's own properties
                    assert.strictEqual(name, "x");
                    assert.strictEqual(type, "object");

                    // The action's execution context
                    assert.deepEqual(context, {
                        active_domain: [],
                        active_id: 1,
                        active_ids: [1],
                        active_model: 'foo',
                        plouf: 'plif',
                    });
                    // The current environment (not owl's, but the current action's)
                    assert.deepEqual(env, {
                        context: {},
                        model: 'foo',
                        resIDs: [1],
                    });
                }
            }
        });
        await testUtils.dom.click(
            list.el.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        const cpButtons = cpHelpers.getButtons(list);
        await testUtils.dom.click(cpButtons[0].querySelector('button[name="x"]'));
        list.destroy();
    });

    QUnit.test('list view: action button executes action on click with domain selected: correct parameters', async function (assert) {
        assert.expect(10);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree limit="1">
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf"/>
                    </header>
                    <field name="foo" />
                </tree>`,
            intercepts: {
                async execute_action(ev) {
                    assert.step('execute_action');
                    const {
                        action_data: {
                            context, name, type
                        },
                        env,
                    } = ev.data;
                    // Action's own properties
                    assert.strictEqual(name, "x");
                    assert.strictEqual(type, "object");

                    // The action's execution context
                    assert.deepEqual(context, {
                        active_domain: [],
                        active_id: 1,
                        active_ids: [1, 2, 3, 4],
                        active_model: 'foo',
                    });
                    // The current environment (not owl's, but the current action's)
                    assert.deepEqual(env, {
                        context: {},
                        model: 'foo',
                        resIDs: [1, 2, 3, 4],
                    });
                }
            },
            mockRPC(route, args) {
                if (args.method === 'search') {
                    assert.step('search');
                    assert.strictEqual(args.model, 'foo');
                    assert.deepEqual(args.args, [[]]); // empty domain since no domain in searchView
                }
                return this._super.call(this, ...arguments);
            }
        });
        await testUtils.dom.click(
            list.el.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        const cpButtons = cpHelpers.getButtons(list);

        await testUtils.dom.click(cpButtons[0].querySelector('.o_list_select_domain'));
        assert.verifySteps([]);

        await testUtils.dom.click(cpButtons[0].querySelector('button[name="x"]'));
        assert.verifySteps([
            'search',
            'execute_action',
        ]);

        list.destroy();
    });

    QUnit.test('column names (noLabel, label, string and default)', async function (assert) {
        assert.expect(4);

        const FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('nolabel_char', FieldChar.extend({
            noLabel: true,
        }));
        fieldRegistry.add('label_char', FieldChar.extend({
            label: "Some static label",
        }));

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="display_name" widget="nolabel_char"/>
                    <field name="foo" widget="label_char"/>
                    <field name="int_field" string="My custom label"/>
                    <field name="text"/>
                </tree>`,
        });

        assert.strictEqual(list.$('thead th[data-name=display_name]').text(), '');
        assert.strictEqual(list.$('thead th[data-name=foo]').text(), 'Some static label');
        assert.strictEqual(list.$('thead th[data-name=int_field]').text(), 'My custom label');
        assert.strictEqual(list.$('thead th[data-name=text]').text(), 'text field');

        list.destroy();
    });

    QUnit.test('simple editable rendering', async function (assert) {
        assert.expect(15);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, 'th', 3, "should have 2 th");
        assert.containsN(list, 'th', 3, "should have 3 th");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);
        assert.containsOnce(list, 'td:contains(yop)', "should contain yop");

        assert.isVisible(list.$buttons.find('.o_list_button_add'),
            "should have a visible Create button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'),
            "should not have a visible save button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_discard'),
            "should not have a visible discard button");

        await testUtils.dom.click(list.$('td:not(.o_list_record_selector)').first());

        assert.isNotVisible(list.$buttons.find('.o_list_button_add'),
            "should not have a visible Create button");
        assert.isVisible(list.$buttons.find('.o_list_button_save'),
            "should have a visible save button");
        assert.isVisible(list.$buttons.find('.o_list_button_discard'),
            "should have a visible discard button");
        assert.containsNone(list, '.o_list_record_selector input:enabled');

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.isVisible(list.$buttons.find('.o_list_button_add'),
            "should have a visible Create button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'),
            "should not have a visible save button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_discard'),
            "should not have a visible discard button");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        list.destroy();
    });

    QUnit.test('editable rendering with handle and no data', async function (assert) {
        assert.expect(6);

        this.data.foo.records = [];
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="currency_id"/>' +
                    '<field name="m2o"/>' +
                '</tree>',
        });
        assert.containsN(list, 'thead th', 4, "there should be 4 th");
        assert.hasClass(list.$('thead th:eq(0)'), 'o_list_record_selector');
        assert.hasClass(list.$('thead th:eq(1)'), 'o_handle_cell');
        assert.strictEqual(list.$('thead th:eq(1)').text(), '',
            "the handle field shouldn't have a header description");
        assert.strictEqual(list.$('thead th:eq(2)').attr('style'), "width: 50%;");
        assert.strictEqual(list.$('thead th:eq(3)').attr('style'), "width: 50%;");
        list.destroy();
    });

    QUnit.test('invisible columns are not displayed', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="1"/>' +
                '</tree>',
        });

        // 1 th for checkbox, 1 for 1 visible column
        assert.containsN(list, 'th', 2, "should have 2 th");
        list.destroy();
    });

    QUnit.test('boolean field has no title', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="bar"/></tree>',
        });
        assert.equal(list.$('tbody tr:first td:eq(1)').attr('title'), "");
        list.destroy();
    });

    QUnit.test('field with nolabel has no title', async function (assert) {
        assert.expect(1);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" nolabel="1"/></tree>',
        });
        assert.strictEqual(list.$('thead tr:first th:eq(1)').text(), "");
        list.destroy();
    });

    QUnit.test('field titles are not escaped', async function (assert) {
        assert.expect(2);

        this.data.foo.records[0].foo = '<div>Hello</div>';

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('tbody tr:first .o_data_cell').text(), "<div>Hello</div>");
        assert.strictEqual(list.$('tbody tr:first .o_data_cell').attr('title'), "<div>Hello</div>");

        list.destroy();
    });

    QUnit.test('record-depending invisible lines are correctly aligned', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody tr:first td', 4,
            "there should be 4 cells in the first row");
        assert.containsOnce(list, 'tbody td.o_invisible_modifier',
            "there should be 1 invisible bar cell");
        assert.hasClass(list.$('tbody tr:first td:eq(2)'),'o_invisible_modifier',
            "the 3rd cell should be invisible");
        assert.containsN(list, 'tbody tr:eq(0) td:visible', list.$('tbody tr:eq(1) td:visible').length,
            "there should be the same number of visible cells in different rows");
        list.destroy();
    });

    QUnit.test('do not perform extra RPC to read invisible many2one fields', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.m2o.default = 2;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="m2o" invisible="1"/>' +
                '</tree>',
            mockRPC: function (route) {
                assert.step(_.last(route.split('/')));
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.verifySteps(['search_read', 'onchange'], "no nameget should be done");

        list.destroy();
    });

    QUnit.test('editable list datetimepicker destroy widget (edition)', async function (assert) {
        assert.expect(7);
        var eventPromise = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
        });
        list.$el.on({
            'show.datetimepicker': async function () {
                assert.containsOnce(list, '.o_selected_row');
                assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget');

                await testUtils.fields.triggerKeydown(list.$('.o_datepicker_input'), 'escape');

                assert.containsOnce(list, '.o_selected_row');
                assert.containsNone($('body'), '.bootstrap-datetimepicker-widget');

                await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');

                assert.containsNone(list, '.o_selected_row');

                eventPromise.resolve();
            }
        });

        assert.containsN(list, '.o_data_row', 4);
        assert.containsNone(list, '.o_selected_row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.dom.openDatepicker(list.$('.o_datepicker'));

        await eventPromise;
        list.destroy();
    });

    QUnit.test('editable list datetimepicker destroy widget (new line)', async function (assert) {
        assert.expect(10);
        var eventPromise = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
        });
        list.$el.on({
            'show.datetimepicker': async function () {
                assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget');
                assert.containsN(list, '.o_data_row', 5);
                assert.containsOnce(list, '.o_selected_row');

                await testUtils.fields.triggerKeydown(list.$('.o_datepicker_input'), 'escape');

                assert.containsNone($('body'), '.bootstrap-datetimepicker-widget');
                assert.containsN(list, '.o_data_row', 5);
                assert.containsOnce(list, '.o_selected_row');

                await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');

                assert.containsN(list, '.o_data_row', 4);
                assert.containsNone(list, '.o_selected_row');

                eventPromise.resolve();
            }
        });
        assert.equal(list.$('.o_data_row').length, 4,
            'There should be 4 rows');

        assert.equal(list.$('.o_selected_row').length, 0,
            'No row should be in edit mode');

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.openDatepicker(list.$('.o_datepicker'));

        await eventPromise;
        list.destroy();
    });

    QUnit.test('at least 4 rows are rendered, even if less data', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="bar"/></tree>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('discard a new record in editable="top" list with less than 4 records', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="bar"/></tree>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(list, '.o_data_row', 3);
        assert.containsN(list, 'tbody tr', 4);

        await testUtils.dom.click(list.$('.o_list_button_add'));

        assert.containsN(list, '.o_data_row', 4);
        assert.hasClass(list.$('tbody tr:first'), 'o_selected_row');

        await testUtils.dom.click(list.$('.o_list_button_discard'));

        assert.containsN(list, '.o_data_row', 3);
        assert.containsN(list, 'tbody tr', 4);
        assert.hasClass(list.$('tbody tr:first'), 'o_data_row');

        list.destroy();
    });

    QUnit.test('basic grouped list rendering', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('th:contains(Foo)').length, 1, "should contain Foo");
        assert.strictEqual(list.$('th:contains(Bar)').length, 1, "should contain Bar");
        assert.containsN(list, 'tr.o_group_header', 2, "should have 2 .o_group_header");
        assert.containsN(list, 'th.o_group_name', 2, "should have 2 .o_group_name");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering with widget="handle" col', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                '</tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('th:contains(Foo)').length, 1, "should contain Foo");
        assert.strictEqual(list.$('th:contains(Bar)').length, 1, "should contain Bar");
        assert.containsN(list, 'tr.o_group_header', 2, "should have 2 .o_group_header");
        assert.containsN(list, 'th.o_group_name', 2, "should have 2 .o_group_name");
        assert.containsNone(list, 'th:contains(int_field)', "Should not have int_field in grouped list");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 1 col without selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "1",
            "the header should span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 1 col with selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "2",
            "the header should span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 2 cols without selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 2,
            "group header should have exactly 2 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "1",
            "the header should not span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 3 cols without selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/><field name="text"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 2,
            "group header should have exactly 2 columns");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "2",
            "the first header should  span two columns");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 2 col with selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 2,
            "group header should have exactly 2 columns");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "2",
            "the header should not span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 3 cols with selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/><field name="text"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 2,
            "group header should have exactly 2 columns");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "3",
            "the header should not span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 7 cols with aggregates and selector', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="datetime"/>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum1"/>' +
                    '<field name="bar"/>' +
                    '<field name="qux" sum="Sum2"/>' +
                    '<field name="date"/>' +
                    '<field name="text"/>' +
                '</tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 5,
            "group header should have exactly 5 columns (one before first aggregate, one after last aggregate, and all in between");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "3",
            "header name should span on the two first fields + selector (colspan 3)");
        assert.containsN(list, '.o_group_header:first td', 3,
            "there should be 3 tds (aggregates + fields in between)");
        assert.strictEqual(list.$('.o_group_header:first th:last').attr('colspan'), "2",
            "header last cell should span on the two last fields (to give space for the pager) (colspan 2)");
        list.destroy();
    });

    QUnit.test('ordered list, sort attribute in context', async function (assert) {
        assert.expect(1);
        // Equivalent to saving a custom filter

        this.data.foo.fields.foo.sortable = true;
        this.data.foo.fields.date.sortable = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="date"/>' +
                '</tree>',
        });

        // Descending order on Foo
        await testUtils.dom.click(list.$('th.o_column_sortable:contains("Foo")'));
        await testUtils.dom.click(list.$('th.o_column_sortable:contains("Foo")'));

        // Ascending order on Date
        await testUtils.dom.click(list.$('th.o_column_sortable:contains("Date")'));

        var listContext = list.getOwnedQueryParams();
        assert.deepEqual(listContext,
            {
                orderedBy: [{
                    name: 'date',
                    asc: true,
                }, {
                    name: 'foo',
                    asc: false,
                }]
            }, 'the list should have the right orderedBy in context');
        list.destroy();
    });

    QUnit.test('Loading a filter with a sort attribute', async function (assert) {
        assert.expect(2);

        this.data.foo.fields.foo.sortable = true;
        this.data.foo.fields.date.sortable = true;

        var searchReads = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="date"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchReads === 0) {
                        assert.strictEqual(args.sort, 'date ASC, foo DESC',
                            'The sort attribute of the filter should be used by the initial search_read');
                    } else if (searchReads === 1) {
                        assert.strictEqual(args.sort, 'date DESC, foo ASC',
                            'The sort attribute of the filter should be used by the next search_read');
                    }
                    searchReads += 1;
                }
                return this._super.apply(this,arguments);
            },
            favoriteFilters : [
                {
                    context: "{}",
                    domain: "[]",
                    id: 7,
                    is_default: true,
                    name: "My favorite",
                    sort: "[\"date asc\", \"foo desc\"]",
                    user_id: [2, "Mitchell Admin"],
                }, {
                    context: "{}",
                    domain: "[]",
                    id: 8,
                    is_default: false,
                    name: "My second favorite",
                    sort: "[\"date desc\", \"foo asc\"]",
                    user_id: [2, "Mitchell Admin"],
                }
            ]
        });


        await cpHelpers.toggleFavoriteMenu(list);
        await cpHelpers.toggleMenuItem(list, "My second favorite");

        list.destroy();
    });

    QUnit.test('many2one field rendering', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="m2o"/></tree>',
        });

        assert.ok(list.$('td:contains(Value 1)').length,
            "should have the display_name of the many2one");
        list.destroy();
    });

    QUnit.test('grouped list view, with 1 open group', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ['foo'],
        });

        await testUtils.dom.click(list.$('th.o_group_name:nth(1)'));
        await testUtils.nextTick();
        assert.containsN(list, 'tbody:eq(1) tr', 2, "open group should contain 2 records");
        assert.containsN(list, 'tbody', 3, "should contain 3 tbody");
        assert.containsOnce(list, 'td:contains(9)', "should contain 9");
        assert.containsOnce(list, 'td:contains(-4)', "should contain -4");
        assert.containsOnce(list, 'td:contains(10)', "should contain 10");
        assert.containsOnce(list, 'tr.o_group_header td:contains(10)', "but 10 should be in a header");
        list.destroy();
    });

    QUnit.test('opening records when clicking on record', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        testUtils.mock.intercept(list, "open_record", function () {
            assert.ok("list view should trigger 'open_record' event");
        });

        await testUtils.dom.click(list.$('tr td:not(.o_list_record_selector)').first());
        list.update({groupBy: ['foo']});
        await testUtils.nextTick();

        assert.containsN(list, 'tr.o_group_header', 3, "list should be grouped");
        await testUtils.dom.click(list.$('th.o_group_name').first());

        testUtils.dom.click(list.$('tr:not(.o_group_header) td:not(.o_list_record_selector)').first());
        list.destroy();
    });

    QUnit.test('editable list view: readonly fields cannot be edited', async function (assert) {
        assert.expect(4);

        this.data.foo.fields.foo.readonly = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="int_field" readonly="1"/>' +
                '</tree>',
        });
        var $td = list.$('td:not(.o_list_record_selector)').first();
        var $second_td = list.$('td:not(.o_list_record_selector)').eq(1);
        var $third_td = list.$('td:not(.o_list_record_selector)').eq(2);
        await testUtils.dom.click($td);
        assert.hasClass($td.parent(),'o_selected_row',
            "row should be in edit mode");
        assert.hasClass($td,'o_readonly_modifier',
            "foo cell should be readonly in edit mode");
        assert.doesNotHaveClass($second_td, 'o_readonly_modifier',
            "bar cell should be editable");
        assert.hasClass($third_td,'o_readonly_modifier',
            "int_field cell should be readonly in edit mode");
        list.destroy();
    });

    QUnit.test('editable list view: line with no active element', async function (assert) {
        assert.expect(3);

        this.data.bar = {
            fields: {
                titi: {string: "Char", type: "char"},
                grosminet: {string: "Bool", type: "boolean"},
            },
            records: [
                {id: 1, titi: 'cui', grosminet: true},
                {id: 2, titi: 'cuicui', grosminet: false},
            ],
        };
        this.data.foo.records[0].o2m = [1, 2];

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>'+
                    '<field name="o2m">'+
                        '<tree editable="top">'+
                            '<field name="titi" readonly="1"/>'+
                            '<field name="grosminet" widget="boolean_toggle"/>'+
                        '</tree>'+
                    '</field>'+
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {
                        o2m: [[1, 1, {grosminet: false}], [4, 2, false]],
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        var $td = form.$('.o_data_cell').first();
        var $td2 = form.$('.o_data_cell').eq(1);
        assert.hasClass($td, 'o_readonly_modifier');
        assert.hasClass($td2, 'o_boolean_toggle_cell');
        await testUtils.dom.click($td);
        await testUtils.dom.click($td2.find('.o_boolean_toggle input'));
        await testUtils.nextTick();

        await testUtils.form.clickSave(form);
        await testUtils.nextTick();
        form.destroy();
    });

    QUnit.test('editable list view: click on last element after creation empty new line', async function (assert) {
        assert.expect(1);

        this.data.bar = {
            fields: {
                titi: {string: "Char", type: "char", required: true},
                int_field: {string: "int_field", type: "integer", sortable: true, required: true}
            },
            records: [
                {id: 1, titi: 'cui', int_field: 2},
                {id: 2, titi: 'cuicui', int_field: 4},
            ],
        };
        this.data.foo.records[0].o2m = [1, 2];

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>'+
                    '<field name="o2m">'+
                        '<tree editable="top">'+
                            '<field name="int_field" widget="handle"/>'+
                            '<field name="titi"/>'+
                        '</tree>'+
                    '</field>'+
                '</form>',
        });
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add > a'));
        await testUtils.dom.click(form.$('.o_data_row:last() > td.o_list_char'));
        // This test ensure that they aren't traceback when clicking on the last row.
        assert.containsN(form, '.o_data_row', 2, "list should have exactly 2 rows");
        form.destroy();
    });

    QUnit.test('edit field in editable field without editing the row', async function (assert) {
        // some widgets are editable in readonly (e.g. priority, boolean_toggle...) and they
        // thus don't require the row to be switched in edition to be edited
        assert.expect(13);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="bar" widget="boolean_toggle"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === 'write') {
                    assert.step('write: ' + args.args[1].bar);
                }
                return this._super(...arguments);
            },
        });

        // toggle the boolean value of the first row without editing the row
        assert.ok(list.$('.o_data_row:first .o_boolean_toggle input')[0].checked);
        assert.containsNone(list, '.o_selected_row');
        await testUtils.dom.click(list.$('.o_data_row:first .o_boolean_toggle'));
        assert.notOk(list.$('.o_data_row:first .o_boolean_toggle input')[0].checked);
        assert.containsNone(list, '.o_selected_row');
        assert.verifySteps(['write: false']);

        // toggle the boolean value after switching the row in edition
        assert.containsNone(list, '.o_selected_row');
        await testUtils.dom.click(list.$('.o_data_row .o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row');
        await testUtils.dom.click(list.$('.o_selected_row .o_boolean_toggle'));
        assert.containsOnce(list, '.o_selected_row');
        assert.verifySteps([]);

        // save
        await testUtils.dom.click(list.$('.o_list_button_save'));
        assert.containsNone(list, '.o_selected_row');
        assert.verifySteps(['write: true']);

        list.destroy();
    });

    QUnit.test('basic operations for editable list renderer', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        var $td = list.$('td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($td.parent(), 'o_selected_row', "td should not be in edit mode");
        await testUtils.dom.click($td);
        assert.hasClass($td.parent(),'o_selected_row', "td should be in edit mode");
        list.destroy();
    });

    QUnit.test('editable list: add a line and discard', async function (assert) {
        assert.expect(11);

        testUtils.mock.patch(basicFields.FieldChar, {
            destroy: function () {
                assert.step('destroy');
                this._super.apply(this, arguments);
            },
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            domain: [['foo', '=', 'yop']],
        });


        assert.containsN(list, 'tbody tr', 4,
            "list should contain 4 rows");
        assert.containsOnce(list, '.o_data_row',
            "list should contain one record (and thus 3 empty rows)");

        assert.strictEqual(cpHelpers.getPagerValue(list), '1-1',
            "pager should be correct");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsN(list, 'tbody tr', 4,
            "list should still contain 4 rows");
        assert.containsN(list, '.o_data_row', 2,
            "list should contain two record (and thus 2 empty rows)");
        assert.strictEqual(cpHelpers.getPagerValue(list), '1-2',
            "pager should be correct");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        assert.containsN(list, 'tbody tr', 4,
            "list should still contain 4 rows");
        assert.containsOnce(list, '.o_data_row',
            "list should contain one record (and thus 3 empty rows)");
        assert.strictEqual(cpHelpers.getPagerValue(list), '1-1',
            "pager should be correct");
        assert.verifySteps(['destroy'],
            "should have destroyed the widget of the removed line");

        testUtils.mock.unpatch(basicFields.FieldChar);
        list.destroy();
    });

    QUnit.test('field changes are triggered correctly', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });
        var $td = list.$('td:not(.o_list_record_selector)').first();

        var n = 0;
        testUtils.mock.intercept(list, "field_changed", function () {
            n += 1;
        });
        await testUtils.dom.click($td);
        await testUtils.fields.editInput($td.find('input'), 'abc');
        assert.strictEqual(n, 1, "field_changed should have been triggered");
        await testUtils.dom.click(list.$('td:not(.o_list_record_selector)').eq(2));
        assert.strictEqual(n, 1, "field_changed should not have been triggered");
        list.destroy();
    });

    QUnit.test('editable list view: basic char field edition', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        var $td = list.$('td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($td);
        await testUtils.fields.editInput($td.find('input'), 'abc');
        assert.strictEqual($td.find('input').val(), 'abc', "char field has been edited correctly");

        var $next_row_td = list.$('tbody tr:eq(1) td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($next_row_td);
        assert.strictEqual(list.$('td:not(.o_list_record_selector)').first().text(), 'abc',
            'changes should be saved correctly');
        assert.doesNotHaveClass(list.$('tbody tr').first(), 'o_selected_row',
            'saved row should be in readonly mode');
        assert.strictEqual(this.data.foo.records[0].foo, 'abc',
            "the edition should have been properly saved");
        list.destroy();
    });

    QUnit.test('editable list view: save data when list sorting in edit mode', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.foo.sortable = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1], {foo: 'xyz'}],
                        "should correctly save the edited record");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('input[name="foo"]'), 'xyz');
        await testUtils.dom.click(list.$('.o_column_sortable'));

        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should still be in edition");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.doesNotHaveClass(list.$buttons, 'o-editing',
            "list buttons should be back to their readonly mode");

        list.destroy();
    });

    QUnit.test('editable list view: check that controlpanel buttons are updating when groupby applied', async function (assert) {
        assert.expect(4);

        this.data.foo.fields.foo = {string: "Foo", type: "char", required:true};

        var actionManager = await createActionManager({
            actions: [{
               id: 11,
               name: 'Partners Action 11',
               res_model: 'foo',
               type: 'ir.actions.act_window',
               views: [[3, 'list']],
               search_view_id: [9, 'search'],
            }],
            archs:  {
               'foo,3,list': '<tree editable="top"><field name="display_name"/><field name="foo"/></tree>',

               'foo,9,search': '<search>'+
                                    '<filter string="candle" name="itsName" context="{\'group_by\': \'foo\'}"/>'  +
                                    '</search>',
            },
            data: this.data,
        });

        await actionManager.doAction(11);
        await testUtils.dom.click(actionManager.$('.o_list_button_add'));

        assert.isNotVisible(actionManager.$('.o_list_button_add'),
            "create button should be invisible");
        assert.isVisible(actionManager.$('.o_list_button_save'), "save button should be visible");

        await testUtils.dom.click(actionManager.$('.o_dropdown_toggler_btn:contains("Group By")'));
        await testUtils.dom.click(actionManager.$('.o_group_by_menu .o_menu_item a:contains("candle")'));

        assert.isNotVisible(actionManager.$('.o_list_button_add'), "create button should be invisible");
        assert.isNotVisible(actionManager.$('.o_list_button_save'),
            "save button should be invisible after applying groupby");

        actionManager.destroy();
    });

    QUnit.test('list view not groupable', async function (assert) {
        assert.expect(2);

        const searchMenuTypesOriginal = ListView.prototype.searchMenuTypes;
        ListView.prototype.searchMenuTypes = ['filter', 'favorite'];

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree editable="top">
                    <field name="display_name"/>
                    <field name="foo"/>
                </tree>
            `,
            archs: {
                'foo,false,search': `
                    <search>
                        <filter context="{'group_by': 'foo'}" name="foo"/>
                    </search>
                `,
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    throw new Error("Should not do a read_group RPC");
                }
                return this._super.apply(this, arguments);
            },
            context: { search_default_foo: 1, },
        });

        assert.containsNone(list, '.o_control_panel div.o_search_options div.o_group_by_menu',
        "there should not be groupby menu");
        assert.deepEqual(cpHelpers.getFacetTexts(list), []);

        list.destroy();
        ListView.prototype.searchMenuTypes = searchMenuTypesOriginal;
    });

    QUnit.test('selection changes are triggered correctly', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });
        var $tbody_selector = list.$('tbody .o_list_record_selector input').first();
        var $thead_selector = list.$('thead .o_list_record_selector input');

        var n = 0;
        testUtils.mock.intercept(list, "selection_changed", function () {
            n += 1;
        });

        // tbody checkbox click
        testUtils.dom.click($tbody_selector);
        assert.strictEqual(n, 1, "selection_changed should have been triggered");
        assert.ok($tbody_selector.is(':checked'), "selection checkbox should be checked");
        testUtils.dom.click($tbody_selector);
        assert.strictEqual(n, 2, "selection_changed should have been triggered");
        assert.ok(!$tbody_selector.is(':checked'), "selection checkbox shouldn't be checked");

        // head checkbox click
        testUtils.dom.click($thead_selector);
        assert.strictEqual(n, 3, "selection_changed should have been triggered");
        assert.containsN(list, 'tbody .o_list_record_selector input:checked',
            list.$('tbody tr').length, "all selection checkboxes should be checked");

        testUtils.dom.click($thead_selector);
        assert.strictEqual(n, 4, "selection_changed should have been triggered");

        assert.containsNone(list, 'tbody .o_list_record_selector input:checked',
                            "no selection checkbox should be checked");
        list.destroy();
    });

    QUnit.test('Row selection checkbox can be toggled by clicking on the cell', async function (assert) {
        assert.expect(9);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });

        testUtils.mock.intercept(list, "selection_changed", function (ev) {
            assert.step(ev.data.selection.length.toString());
        });

        testUtils.dom.click(list.$('tbody .o_list_record_selector:first'));
        assert.containsOnce(list, 'tbody .o_list_record_selector input:checked');
        testUtils.dom.click(list.$('tbody .o_list_record_selector:first'));
        assert.containsNone(list, '.o_list_record_selector input:checked');

        testUtils.dom.click(list.$('thead .o_list_record_selector'));
        assert.containsN(list, '.o_list_record_selector input:checked', 5);
        testUtils.dom.click(list.$('thead .o_list_record_selector'));
        assert.containsNone(list, '.o_list_record_selector input:checked');

        assert.verifySteps(['1', '0', '4', '0']);

        list.destroy();
    });

    QUnit.test('head selector is toggled by the other selectors', async function (assert) {
        assert.expect(6);

        const list = await createView({
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            data: this.data,
            groupBy: ['bar'],
            model: 'foo',
            View: ListView,
        });

        assert.ok(!list.$('thead .o_list_record_selector input')[0].checked,
            "Head selector should be unchecked");

        await testUtils.dom.click(list.$('.o_group_header:first()'));
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        assert.containsN(list, 'tbody .o_list_record_selector input:checked',
            3, "All visible checkboxes should be checked");

        await testUtils.dom.click(list.$('.o_group_header:last()'));

        assert.ok(!list.$('thead .o_list_record_selector input')[0].checked,
            "Head selector should be unchecked");

        await testUtils.dom.click(list.$('tbody .o_list_record_selector input:last()'));

        assert.ok(list.$('thead .o_list_record_selector input')[0].checked,
            "Head selector should be checked");

        await testUtils.dom.click(list.$('tbody .o_list_record_selector:first() input'));

        assert.ok(!list.$('thead .o_list_record_selector input')[0].checked,
            "Head selector should be unchecked");

        await testUtils.dom.click(list.$('.o_group_header:first()'));

        assert.ok(list.$('thead .o_list_record_selector input')[0].checked,
            "Head selector should be checked");

        list.destroy();
    });

    QUnit.test('selection box is properly displayed (single page)', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, '.o_data_row', 4);
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box');

        // select a record
        await testUtils.dom.click(list.$('.o_data_row:first .o_list_record_selector input'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');
        assert.strictEqual(list.$('.o_list_selection_box').text().trim(), '1 selected');

        // select all records of first page
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');
        assert.strictEqual(list.$('.o_list_selection_box').text().trim(), '4 selected');

        // unselect a record
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_list_record_selector input'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');
        assert.strictEqual(list.$('.o_list_selection_box').text().trim(), '3 selected');

        list.destroy();
    });

    QUnit.test('selection box is properly displayed (multi pages)', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="3"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, '.o_data_row', 3);
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box');

        // select a record
        await testUtils.dom.click(list.$('.o_data_row:first .o_list_record_selector input'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');
        assert.strictEqual(list.$('.o_list_selection_box').text().trim(), '1 selected');

        // select all records of first page
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.containsOnce(list.$('.o_list_selection_box'), '.o_list_select_domain');
        assert.strictEqual(list.$('.o_list_selection_box').text().replace(/\s+/g, ' ').trim(),
            '3 selected Select all 4');

        // select all domain
        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.strictEqual(list.$('.o_list_selection_box').text().trim(), 'All 4 selected');

        list.destroy();
    });

    QUnit.test('selection box is removed after multi record edition', async function (assert) {
        assert.expect(6);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, '.o_data_row', 4,
            "there should be 4 records");
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box',
            "list selection box should not be displayed");

        // select all records
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box',
            "list selection box should be displayed");
        assert.containsN(list, '.o_data_row .o_list_record_selector input:checked', 4,
            "all 4 records should be selected");

        // edit selected records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'legion');
        await testUtils.dom.click($('.modal-dialog button.btn-primary'));
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box',
            "list selection box should not be displayed");
        assert.containsNone(list, '.o_data_row .o_list_record_selector input:checked',
            "no records should be selected");

        list.destroy();
    });

    QUnit.test('selection is reset on reload', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum"/>' +
                '</tree>',
        });

        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32',
            "total should be 32 (no record selected)");

        // select first record
        var $firstRowSelector = list.$('tbody .o_list_record_selector input').first();
        testUtils.dom.click($firstRowSelector);
        assert.ok($firstRowSelector.is(':checked'), "first row should be selected");
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '10',
            "total should be 10 (first record selected)");

        // reload
        await list.reload();
        $firstRowSelector = list.$('tbody .o_list_record_selector input').first();
        assert.notOk($firstRowSelector.is(':checked'),
            "first row should no longer be selected");
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box');
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32',
            "total should be 32 (no more record selected)");

        list.destroy();
    });

    QUnit.test('selection is kept on render without reload', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            viewOptions: {hasActionMenus: true},
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum"/>' +
                '</tree>',
        });

        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box');

        // open blip grouping and check all lines
        await testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        await testUtils.dom.click(list.$('.o_data_row:first input'));
        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');

        // open yop grouping and verify blip are still checked
        await testUtils.dom.click(list.$('.o_group_header:contains("yop (1)")'));
        assert.containsOnce(list, '.o_data_row input:checked',
            "opening a grouping does not uncheck others");
        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsOnce(list.$('.o_cp_buttons'), '.o_list_selection_box');

        // close and open blip grouping and verify blip are unchecked
        await testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        await testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        assert.containsNone(list, '.o_data_row input:checked',
            "opening and closing a grouping uncheck its elements");
        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsNone(list.$('.o_cp_buttons'), '.o_list_selection_box');

        list.destroy();
    });

    QUnit.test('aggregates are computed correctly', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" sum="Sum"/></tree>',
        });
        var $tbody_selectors = list.$('tbody .o_list_record_selector input');
        var $thead_selector = list.$('thead .o_list_record_selector input');

        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32", "total should be 32");

        testUtils.dom.click($tbody_selectors.first());
        testUtils.dom.click($tbody_selectors.last());
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "6",
                        "total should be 6 as first and last records are selected");

        testUtils.dom.click($thead_selector);
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32",
                        "total should be 32 as all records are selected");

        // Let's update the view to dislay NO records
        await list.update({domain: ['&', ['bar', '=', false], ['int_field', '>', 0]]});
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "0", "total should have been recomputed to 0");

        list.destroy();
    });

    QUnit.test('aggregates are computed correctly in grouped lists', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['m2o'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
        });

        var $groupHeader1 = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 1;
        });
        var $groupHeader2 = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 2;
        });
        assert.strictEqual($groupHeader1.find('td:last()').text(), "23", "first group total should be 23");
        assert.strictEqual($groupHeader2.find('td:last()').text(), "9", "second group total should be 9");
        assert.strictEqual(list.$('tfoot td:last()').text(), "32", "total should be 32");

        await testUtils.dom.click($groupHeader1);
        await testUtils.dom.click(list.$('tbody .o_list_record_selector input').first());
        assert.strictEqual(list.$('tfoot td:last()').text(), "10",
                        "total should be 10 as first record of first group is selected");
        list.destroy();
    });

    QUnit.test('aggregates are updated when a line is edited', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="int_field" sum="Sum"/></tree>',
        });

        assert.strictEqual(list.$('td[title="Sum"]').text(), "32", "current total should be 32");

        await testUtils.dom.click(list.$('tr.o_data_row td.o_data_cell').first());
        await testUtils.fields.editInput(list.$('td.o_data_cell input'), "15");

        assert.strictEqual(list.$('td[title="Sum"]').text(), "37",
            "current total should now be 37");
        list.destroy();
    });

    QUnit.test('aggregates are formatted according to field widget', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="qux" widget="float_time" sum="Sum"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '19:24',
            "total should be formatted as a float_time");

        list.destroy();
    });

    QUnit.test('aggregates digits can be set with digits field attribute', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="amount" widget="monetary" sum="Sum" digits="[69,3]"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('.o_data_row td:nth(1)').text(), '1200.00',
            "field should still be formatted based on currency");
        assert.strictEqual(list.$('tfoot td:nth(1)').text(), '2000.000',
            "aggregates monetary use digits attribute if available");

        list.destroy();
    });

    QUnit.test('groups can be sorted on aggregates', async function (assert) {
        assert.expect(10);
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody .o_list_number').text(), '10517',
            "initial order should be 10, 5, 17");
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should be 32");

        await testUtils.dom.click(list.$('.o_column_sortable'));
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should still be 32");
        assert.strictEqual(list.$('tbody .o_list_number').text(), '51017',
            "order should be 5, 10, 17");

        await testUtils.dom.click(list.$('.o_column_sortable'));
        assert.strictEqual(list.$('tbody .o_list_number').text(), '17105',
            "initial order should be 17, 10, 5");
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should still be 32");

        assert.verifySteps(['default order', 'int_field ASC', 'int_field DESC']);

        list.destroy();
    });

    QUnit.test('groups cannot be sorted on non-aggregable fields', async function (assert) {
        assert.expect(6);
        this.data.foo.fields.sort_field = {string: "sortable_field", type: "sting", sortable: true, default: "value"};
        _.each(this.data.records, function (elem) {
            elem.sort_field = "value" + elem.id;
        });
        this.data.foo.fields.foo.sortable = true;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field"/><field name="sort_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });
        //we cannot sort by sort_field since it doesn't have a group_operator
        await testUtils.dom.click(list.$('.o_column_sortable:eq(2)'));
        //we can sort by int_field since it has a group_operator
        await testUtils.dom.click(list.$('.o_column_sortable:eq(1)'));
        //we keep previous order
        await testUtils.dom.click(list.$('.o_column_sortable:eq(2)'));
        //we can sort on foo since we are groupped by foo + previous order
        await testUtils.dom.click(list.$('.o_column_sortable:eq(0)'));

        assert.verifySteps([
            'default order',
            'default order',
            'int_field ASC',
            'int_field ASC',
            'foo ASC, int_field ASC'
        ]);

        list.destroy();
    });

    QUnit.test('properly apply onchange in simple case', async function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        var $foo_td = list.$('td:not(.o_list_record_selector)').first();
        var $int_field_td = list.$('td:not(.o_list_record_selector)').eq(1);

        assert.strictEqual($int_field_td.text(), '10', "should contain initial value");

        await testUtils.dom.click($foo_td);
        await testUtils.fields.editInput($foo_td.find('input'), 'tralala');

        assert.strictEqual($int_field_td.find('input').val(), "1007",
                        "should contain input with onchange applied");
        list.destroy();
    });

    QUnit.test('column width should not change when switching mode', async function (assert) {
        assert.expect(4);

        // Warning: this test is css dependant
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                        '<field name="int_field" readonly="1"/>' +
                        '<field name="m2o"/>' +
                        '<field name="m2m" widget="many2many_tags"/>' +
                    '</tree>',
        });

        var startWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var startWidth = list.$('table').addBack('table').width();

        // start edition of first row
        await testUtils.dom.click(list.$('td:not(.o_list_record_selector)').first());

        var editionWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var editionWidth = list.$('table').addBack('table').width();

        // leave edition
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        var readonlyWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var readonlyWidth = list.$('table').addBack('table').width();

        assert.strictEqual(editionWidth, startWidth,
            "table should have kept the same width when switching from readonly to edit mode");
        assert.deepEqual(editionWidths, startWidths,
            "width of columns should remain unchanged when switching from readonly to edit mode");
        assert.strictEqual(readonlyWidth, editionWidth,
            "table should have kept the same width when switching from edit to readonly mode");
        assert.deepEqual(readonlyWidths, editionWidths,
            "width of columns should remain unchanged when switching from edit to readonly mode");

        list.destroy();
    });

    QUnit.test('column widths should depend on the content when there is data', async function (assert) {
        assert.expect(1);

        this.data.foo.records[0].foo = 'Some very very long value for a char field';

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="bar"/>' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                        '<field name="qux"/>' +
                        '<field name="date"/>' +
                        '<field name="datetime"/>' +
                    '</tree>',
            viewOptions: {
                limit: 2,
            },
        });
        var widthPage1 = list.$(`th[data-name=foo]`)[0].offsetWidth;

        await cpHelpers.pagerNext(list);

        var widthPage2 = list.$(`th[data-name=foo]`)[0].offsetWidth;
        assert.ok(widthPage1 > widthPage2,
            'column widths should be computed dynamically according to the content');

        list.destroy();
    });

    QUnit.test('width of some of the fields should be hardcoded if no data', async function (assert) {
        const assertions = [
            { field: 'bar', expected: 70, type: 'Boolean' },
            { field: 'int_field', expected: 74, type: 'Integer' },
            { field: 'qux', expected: 92, type: 'Float' },
            { field: 'date', expected: 92, type: 'Date' },
            { field: 'datetime', expected: 146, type: 'Datetime' },
            { field: 'amount', expected: 104, type: 'Monetary' },
        ];
        assert.expect(9);

        this.data.foo.records = [];
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="bar"/>' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                        '<field name="qux"/>' +
                        '<field name="date"/>' +
                        '<field name="datetime"/>' +
                        '<field name="amount"/>' +
                        '<field name="currency_id" width="25px"/>' +
                    '</tree>',
        });

        assert.containsNone(list, '.o_resize', "There shouldn't be any resize handle if no data");
        assertions.forEach(a => {
            assert.strictEqual(list.$(`th[data-name="${a.field}"]`)[0].offsetWidth, a.expected,
                `Field ${a.type} should have a fixed width of ${a.expected} pixels`);
        });
        assert.strictEqual(list.$('th[data-name="foo"]')[0].style.width, '100%',
            "Char field should occupy the remaining space");
        assert.strictEqual(list.$('th[data-name="currency_id"]')[0].offsetWidth, 25,
            'Currency field should have a fixed width of 25px (see arch)');

        list.destroy();
    });

    QUnit.test('width of some fields should be hardcoded if no data, and list initially invisible', async function (assert) {
        const assertions = [
            { field: 'bar', expected: 70, type: 'Boolean' },
            { field: 'int_field', expected: 74, type: 'Integer' },
            { field: 'qux', expected: 92, type: 'Float' },
            { field: 'date', expected: 92, type: 'Date' },
            { field: 'datetime', expected: 146, type: 'Datetime' },
            { field: 'amount', expected: 104, type: 'Monetary' },
        ];
        assert.expect(12);

        this.data.foo.fields.foo_o2m = {string: "Foo O2M", type: "one2many", relation: "foo"};
        const form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: `<form>
                    <sheet>
                        <notebook>
                            <page string="Page1"></page>
                            <page string="Page2">
                                <field name="foo_o2m">
                                    <tree editable="bottom">
                                        <field name="bar"/>
                                        <field name="foo"/>
                                        <field name="int_field"/>
                                        <field name="qux"/>
                                        <field name="date"/>
                                        <field name="datetime"/>
                                        <field name="amount"/>
                                        <field name="currency_id" width="25px"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
        });

        assert.isNotVisible(form.$('.o_field_one2many'));

        await testUtils.dom.click(form.$('.nav-item:last-child .nav-link'));

        assert.isVisible(form.$('.o_field_one2many'));

        assert.containsNone(form, '.o_field_one2many .o_resize',
            "There shouldn't be any resize handle if no data");
        assertions.forEach(a => {
            assert.strictEqual(form.$(`.o_field_one2many th[data-name="${a.field}"]`)[0].offsetWidth, a.expected,
                `Field ${a.type} should have a fixed width of ${a.expected} pixels`);
        });
        assert.strictEqual(form.$('.o_field_one2many th[data-name="foo"]')[0].style.width, '100%',
            "Char field should occupy the remaining space");
        assert.strictEqual(form.$('th[data-name="currency_id"]')[0].offsetWidth, 25,
            'Currency field should have a fixed width of 25px (see arch)');
        assert.strictEqual(form.el.querySelector('.o_list_record_remove_header').style.width, '32px');

        form.destroy();
    });

    QUnit.test('empty editable list with the handle widget and no content help', async function (assert) {
        assert.expect(4);

        // no records for the foo model
        this.data.foo.records = [];

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `<tree editable="bottom">
                    <field name="int_field" widget="handle" />
                    <field name="foo" />
                </tree>`,
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a foo</p>'
                }
            },
        });

        // as help is being provided in the action, table won't be rendered until a record exists
        assert.containsNone(list, '.o_list_table', " there should not be any records in the view.");
        assert.containsOnce(list, '.o_view_nocontent', "should have no content help");

        // click on create button
        await testUtils.dom.click(list.$('.o_list_button_add'));
        const handleWidgetMinWidth = "33px";
        const handleWidgetHeader = list.$('thead > tr > th.o_handle_cell');
        assert.strictEqual(handleWidgetHeader.css('min-width'), handleWidgetMinWidth,
            "While creating first record, min-width should be applied to handle widget.");

        // creating one record
        await testUtils.fields.editInput(list.$("tr.o_selected_row input[name='foo']"), 'test_foo');
        await testUtils.dom.click(list.$('.o_list_button_save'));
        assert.strictEqual(handleWidgetHeader.css('min-width'), handleWidgetMinWidth,
            "After creation of the first record, min-width of the handle widget should remain as it is");

        list.destroy();
    });

    QUnit.test('editable list: overflowing table', async function (assert) {
        assert.expect(1);

        this.data.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet: { string: "Beeg char", type: "char", sortable: true },
            },
            records: [
                {
                    id: 1,
                    titi: "Tiny text",
                    grosminet:
                        // Just want to make sure that the table is overflowed
                        `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                        Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                        velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                        ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                        Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                        Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                        eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                        nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                        efficitur aliquet.`,
                },
            ],
        };
        const list = await createView({
            arch: `
                <tree editable="top">
                    <field name="titi"/>
                    <field name="grosminet" widget="char"/>
                </tree>`,
            data: this.data,
            model: 'bar',
            View: ListView,
        });

        assert.strictEqual(list.$('table').width(), list.$('.o_list_view').width(),
            "Table should not be stretched by its content");

        list.destroy();
    });

    QUnit.test('editable list: overflowing table (3 columns)', async function (assert) {
        assert.expect(4);

        const longText = `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                        Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                        velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                        ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                        Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                        Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                        eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                        nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                        efficitur aliquet.`;

        this.data.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet1: { string: "Beeg char 1", type: "char", sortable: true },
                grosminet2: { string: "Beeg char 2", type: "char", sortable: true },
                grosminet3: { string: "Beeg char 3", type: "char", sortable: true },
            },
            records: [{
                id: 1,
                titi: "Tiny text",
                grosminet1: longText,
                grosminet2: longText + longText,
                grosminet3: longText + longText + longText,
            }],
        };
        const list = await createView({
            arch: `
                <tree editable="top">
                    <field name="titi"/>
                    <field name="grosminet1" class="large"/>
                    <field name="grosminet3" class="large"/>
                    <field name="grosminet2" class="large"/>
                </tree>`,
            data: this.data,
            model: 'bar',
            View: ListView,
        });

        assert.strictEqual(list.$('table').width(), list.$('.o_list_view').width());
        const largeCells = list.$('.o_data_cell.large');
        assert.strictEqual(largeCells[0].offsetWidth, largeCells[1].offsetWidth);
        assert.strictEqual(largeCells[1].offsetWidth, largeCells[2].offsetWidth);
        assert.ok(list.$('.o_data_cell:not(.large)')[0].offsetWidth < largeCells[0].offsetWidth);

        list.destroy();
    });

    QUnit.test('editable list: list view in an initially unselected notebook page', async function (assert) {
        assert.expect(5);

        this.data.foo.records = [{ id: 1, o2m: [1] }];
        this.data.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet: { string: "Beeg char", type: "char", sortable: true },
            },
            records: [
                {
                    id: 1,
                    titi: "Tiny text",
                    grosminet:
                        'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ' +
                        'Ut at nisi congue, facilisis neque nec, pulvinar nunc. ' +
                        'Vivamus ac lectus velit.',
                },
            ],
        };
        const form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>' +
                    '<sheet>' +
                        '<notebook>' +
                            '<page string="Page1"></page>' +
                            '<page string="Page2">' +
                                '<field name="o2m">' +
                                    '<tree editable="bottom">' +
                                        '<field name="titi"/>' +
                                        '<field name="grosminet"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
        });

        const [titi, grosminet] = form.el.querySelectorAll('.tab-pane:last-child th');
        const one2many = form.el.querySelector('.o_field_one2many');

        assert.isNotVisible(one2many,
            "One2many field should be hidden");
        assert.strictEqual(titi.style.width, "",
            "width of small char should not be set yet");
        assert.strictEqual(grosminet.style.width, "",
            "width of large char should also not be set");

        await testUtils.dom.click(form.el.querySelector('.nav-item:last-child .nav-link'));

        assert.isVisible(one2many,
            "One2many field should be visible");
        assert.ok(
            titi.style.width.split('px')[0] > 80 &&
            grosminet.style.width.split('px')[0] > 700,
            "list has been correctly frozen after being visible");

        form.destroy();
    });

    QUnit.test('editable list: list view hidden by an invisible modifier', async function (assert) {
        assert.expect(5);

        this.data.foo.records = [{ id: 1, bar: true, o2m: [1] }];
        this.data.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet: { string: "Beeg char", type: "char", sortable: true },
            },
            records: [
                {
                    id: 1,
                    titi: "Tiny text",
                    grosminet:
                        'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ' +
                        'Ut at nisi congue, facilisis neque nec, pulvinar nunc. ' +
                        'Vivamus ac lectus velit.',
                },
            ],
        };
        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="bar"/>' +
                        '<field name="o2m" attrs="{\'invisible\': [(\'bar\', \'=\', True)]}">' +
                            '<tree editable="bottom">' +
                                '<field name="titi"/>' +
                                '<field name="grosminet"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
        });

        const [titi, grosminet] = form.el.querySelectorAll('th');
        const one2many = form.el.querySelector('.o_field_one2many');

        assert.isNotVisible(one2many,
            "One2many field should be hidden");
        assert.strictEqual(titi.style.width, "",
            "width of small char should not be set yet");
        assert.strictEqual(grosminet.style.width, "",
            "width of large char should also not be set");

        await testUtils.dom.click(form.el.querySelector('.o_field_boolean input'));

        assert.isVisible(one2many,
            "One2many field should be visible");
        assert.ok(
            titi.style.width.split('px')[0] > 80 &&
            grosminet.style.width.split('px')[0] > 700,
            "list has been correctly frozen after being visible");

        form.destroy();
    });

    QUnit.test('editable list: updating list state while invisible', async function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            bar: function (obj) {
                obj.o2m = [[5], [0, null, { display_name: "Whatever" }]];
            },
        };
        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="bar"/>' +
                        '<notebook>' +
                            '<page string="Page 1"></page>' +
                            '<page string="Page 2">' +
                                '<field name="o2m">' +
                                    '<tree editable="bottom">' +
                                        '<field name="display_name"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
        });

        await testUtils.dom.click(form.$('.o_field_boolean input'));

        assert.strictEqual(form.el.querySelector('th').style.width, "",
            "Column header should be initially unfrozen");

        await testUtils.dom.click(form.$('.nav-item:last() .nav-link'));

        assert.notEqual(form.el.querySelector('th').style.width, "",
            "Column header should have been frozen");

        form.destroy();
    });

    QUnit.test('empty list: state with nameless and stringless buttons', async function (assert) {
        assert.expect(2);

        this.data.foo.records = [];
        const list = await createView({
            arch: `
                <tree>
                    <field name="foo"/>
                    <button string="choucroute"/>
                    <button icon="fa-heart"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        assert.strictEqual(list.el.querySelector('th[data-name="foo"]').style.width, '50%',
            "Field column should be frozen");
        assert.strictEqual(list.el.querySelector('th:last-child').style.width, '50%',
            "Buttons column should be frozen");

        list.destroy();
    });

    QUnit.test('editable list: unnamed columns cannot be resized', async function (assert) {
        assert.expect(2);

        this.data.foo.records = [{ id: 1, o2m: [1] }];
        this.data.bar.records = [{ id: 1, display_name: "Oui" }];
        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="top">' +
                                '<field name="display_name"/>' +
                                '<button name="the_button" icon="fa-heart"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
        });

        const [charTh, buttonTh] = form.$('.o_field_one2many th');
        const thRect = charTh.getBoundingClientRect();
        const resizeRect = charTh.getElementsByClassName('o_resize')[0].getBoundingClientRect();

        assert.strictEqual(thRect.x + thRect.width, resizeRect.x + resizeRect.width,
            "First resize handle should be attached at the end of the first header");
        assert.containsNone(buttonTh, '.o_resize',
            "Columns without name should not have a resize handle");

        form.destroy();
    });

    QUnit.test('width of some of the fields should be hardcoded if no data (grouped case)', async function (assert) {
        const assertions = [
            { field: 'bar', expected: 70, type: 'Boolean' },
            { field: 'int_field', expected: 74, type: 'Integer' },
            { field: 'qux', expected: 92, type: 'Float' },
            { field: 'date', expected: 92, type: 'Date' },
            { field: 'datetime', expected: 146, type: 'Datetime' },
            { field: 'amount', expected: 104, type: 'Monetary' },
        ];
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="bar"/>' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                        '<field name="qux"/>' +
                        '<field name="date"/>' +
                        '<field name="datetime"/>' +
                        '<field name="amount"/>' +
                        '<field name="currency_id" width="25px"/>' +
                    '</tree>',
            groupBy: ['int_field'],
        });

        assert.containsNone(list, '.o_resize', "There shouldn't be any resize handle if no data");
        assertions.forEach(a => {
            assert.strictEqual(list.$(`th[data-name="${a.field}"]`)[0].offsetWidth, a.expected,
                `Field ${a.type} should have a fixed width of ${a.expected} pixels`);
        });
        assert.strictEqual(list.$('th[data-name="foo"]')[0].style.width, '100%',
            "Char field should occupy the remaining space");
        assert.strictEqual(list.$('th[data-name="currency_id"]')[0].offsetWidth, 25,
            "Currency field should have a fixed width of 25px (see arch)");

        list.destroy();
    });

    QUnit.test('column width should depend on the widget', async function (assert) {
        assert.expect(1);

        this.data.foo.records = []; // the width heuristic only applies when there are no records
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="datetime" widget="date"/>' +
                        '<field name="text"/>' +
                    '</tree>',
        });

        assert.strictEqual(list.$('th[data-name="datetime"]')[0].offsetWidth, 92,
            "should be the optimal width to display a date, not a datetime");

        list.destroy();
    });

    QUnit.test('column widths are kept when adding first record', async function (assert) {
        assert.expect(2);

        this.data.foo.records = []; // in this scenario, we start with no records
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="datetime"/>' +
                        '<field name="text"/>' +
                    '</tree>',
        });

        var width = list.$('th[data-name="datetime"]')[0].offsetWidth;

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsOnce(list, '.o_data_row');
        assert.strictEqual(list.$('th[data-name="datetime"]')[0].offsetWidth, width);

        list.destroy();
    });

    QUnit.test('column widths are kept when editing a record', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                        '<field name="datetime"/>' +
                        '<field name="text"/>' +
                    '</tree>',
        });

        var width = list.$('th[data-name="datetime"]')[0].offsetWidth;

        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        assert.containsOnce(list, '.o_selected_row');

        var longVal = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, ' +
            'justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum purus ' +
            'bibendum est.';
        await testUtils.fields.editInput(list.$('.o_field_widget[name=text]'), longVal);
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.containsNone(list, '.o_selected_row');
        assert.strictEqual(list.$('th[data-name="datetime"]')[0].offsetWidth, width);

        list.destroy();
    });

    QUnit.test('column widths are kept when switching records in edition', async function (assert) {
        assert.expect(4);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `<tree editable="bottom">
                    <field name="m2o"/>
                    <field name="text"/>
                </tree>`,
        });

        const width = list.$('th[data-name="m2o"]')[0].offsetWidth;

        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.strictEqual(list.$('th[data-name="m2o"]')[0].offsetWidth, width);

        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(list.$('th[data-name="m2o"]')[0].offsetWidth, width);

        list.destroy();
    });

    QUnit.test('column widths are re-computed on window resize', async function (assert) {
        assert.expect(2);

        testUtils.mock.patch(ListRenderer, {
            RESIZE_DELAY: 0,
        });

        this.data.foo.records[0].text = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ' +
            'Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ' +
            'ipsum purus bibendum est.';
        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `<tree editable="bottom">
                        <field name="datetime"/>
                        <field name="text"/>
                    </tree>`,
        });

        const initialTextWidth = list.$('th[data-name="text"]')[0].offsetWidth;
        const selectorWidth = list.$('th.o_list_record_selector')[0].offsetWidth;

        // simulate a window resize
        list.$el.width(`${list.$el.width() / 2}px`);
        core.bus.trigger('resize');
        await testUtils.nextTick();

        const postResizeTextWidth = list.$('th[data-name="text"]')[0].offsetWidth;
        const postResizeSelectorWidth = list.$('th.o_list_record_selector')[0].offsetWidth;
        assert.ok(postResizeTextWidth < initialTextWidth);
        assert.strictEqual(selectorWidth, postResizeSelectorWidth);

        testUtils.mock.unpatch(ListRenderer);
        list.destroy();
    });

    QUnit.test('columns with an absolute width are never narrower than that width', async function (assert) {
        assert.expect(2);

        this.data.foo.records[0].text = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, ' +
            'sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim ' +
            'veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo ' +
            'consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum ' +
            'dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, ' +
            'sunt in culpa qui officia deserunt mollit anim id est laborum';
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                        '<field name="datetime"/>' +
                        '<field name="int_field" width="200px"/>' +
                        '<field name="text"/>' +
                    '</tree>',
        });

        assert.strictEqual(list.$('th[data-name="datetime"]')[0].offsetWidth, 146);
        assert.strictEqual(list.$('th[data-name="int_field"]')[0].offsetWidth, 200);

        list.destroy();
    });

    QUnit.test('list view with data: text columns are not crushed', async function (assert) {
        assert.expect(2);

        const longText = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do ' +
            'eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim ' +
            'veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo ' +
            'consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum ' +
            'dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, ' +
            'sunt in culpa qui officia deserunt mollit anim id est laborum';
        this.data.foo.records[0].foo = longText;
        this.data.foo.records[0].text = longText;
        this.data.foo.records[1].foo = "short text";
        this.data.foo.records[1].text = "short text";
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="text"/></tree>',
        });

        const fooWidth = list.$('th[data-name="foo"]')[0].offsetWidth;
        const textWidth = list.$('th[data-name="text"]')[0].offsetWidth;
        assert.strictEqual(fooWidth, textWidth, "both columns should have been given the same width");

        const firstRowHeight = list.$('.o_data_row:nth(0)')[0].offsetHeight;
        const secondRowHeight = list.$('.o_data_row:nth(1)')[0].offsetHeight;
        assert.ok(firstRowHeight > secondRowHeight,
            "in the first row, the (long) text field should be properly displayed on several lines");

        list.destroy();
    });

    QUnit.test("button in a list view with a default relative width", async function (assert) {
        assert.expect(1);

        const list = await createView({
            arch: `
            <tree>
                <field name="foo"/>
                <button name="the_button" icon="fa-heart" width="0.1"/>
            </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        assert.strictEqual(list.el.querySelector('.o_data_cell button').style.width, "",
            "width attribute should not change the CSS style");

        list.destroy();
    });

    QUnit.test("button columns in a list view don't have a max width", async function (assert) {
        assert.expect(2);

        testUtils.mock.patch(ListRenderer, {
            RESIZE_DELAY: 0,
        });

        // set a long foo value s.t. the column can be squeezed
        this.data.foo.records[0].foo = 'Lorem ipsum dolor sit amet';
        const list = await createView({
            arch: `
                <tree>
                    <field name="foo"/>
                    <button name="b1" string="Do This"/>
                    <button name="b2" string="Do That"/>
                    <button name="b3" string="Or Rather Do Something Else"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        // simulate a window resize (buttons column width should not be squeezed)
        list.$el.width('300px');
        core.bus.trigger('resize');
        await testUtils.nextTick();

        assert.strictEqual(list.$('th:nth(1)').css('max-width'), '92px',
            "max-width should be set on column foo to the minimum column width (92px)");
        assert.strictEqual(list.$('th:nth(2)').css('max-width'), '100%',
            "no max-width should be harcoded on the buttons column");

        testUtils.mock.unpatch(ListRenderer);
        list.destroy();
    });

    QUnit.test('column widths are kept when editing multiple records', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="datetime"/>' +
                        '<field name="text"/>' +
                    '</tree>',
        });

        var width = list.$('th[data-name="datetime"]')[0].offsetWidth;

        // select two records and edit
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));

        assert.containsOnce(list, '.o_selected_row');
        var longVal = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, ' +
            'justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum purus ' +
            'bibendum est.';
        await testUtils.fields.editInput(list.$('.o_field_widget[name=text]'), longVal);
        assert.containsOnce(document.body, '.modal');
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.containsNone(list, '.o_selected_row');
        assert.strictEqual(list.$('th[data-name="datetime"]')[0].offsetWidth, width);

        list.destroy();
    });

    QUnit.test('row height and width should not change when switching mode', async function (assert) {
        // Warning: this test is css dependant
        assert.expect(5);

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        this.data.foo.fields.foo.translate = true;
        this.data.foo.fields.boolean = {type: 'boolean', string: 'Bool'};
        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo" required="1"/>' +
                        '<field name="int_field" readonly="1"/>' +
                        '<field name="boolean"/>' +
                        '<field name="date"/>' +
                        '<field name="text"/>' +
                        '<field name="amount"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                        '<field name="m2o"/>' +
                        '<field name="m2m" widget="many2many_tags"/>' +
                    '</tree>',
            session: {
                currencies: currencies,
            },
        });

        // the width is hardcoded to make sure we have the same condition
        // between debug mode and non debug mode
        list.$el.width('1200px');
        var startHeight = list.$('.o_data_row:first').outerHeight();
        var startWidth = list.$('.o_data_row:first').outerWidth();

        // start edition of first row
        await testUtils.dom.click(list.$('.o_data_row:first > td:not(.o_list_record_selector)').first());
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        var editionHeight = list.$('.o_data_row:first').outerHeight();
        var editionWidth = list.$('.o_data_row:first').outerWidth();

        // leave edition
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        var readonlyHeight = list.$('.o_data_row:first').outerHeight();
        var readonlyWidth = list.$('.o_data_row:first').outerWidth();

        assert.strictEqual(startHeight, editionHeight);
        assert.strictEqual(startHeight, readonlyHeight);
        assert.strictEqual(startWidth, editionWidth);
        assert.strictEqual(startWidth, readonlyWidth);

        _t.database.multi_lang = multiLang;
        list.destroy();
    });

    QUnit.test('fields are translatable in list view', async function (assert) {
        assert.expect(3);

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;
        this.data.foo.fields.foo.translate = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_button" && args.method === 'translate_fields') {
                    return Promise.resolve({
                        domain: [],
                        context: {search_default_name: 'foo,foo'},
                    });
                }
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([["en_US","English"], ["fr_BE", "Frenglish"]]);
                }
                return this._super.apply(this, arguments);
            },
            arch: '<tree editable="top">' +
                        '<field name="foo" required="1"/>' +
                    '</tree>',
        });

        await testUtils.dom.click(list.$('.o_data_row:first > td:not(.o_list_record_selector)').first());
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        await testUtils.dom.click(list.$('input.o_field_translate+span.o_field_translate'));
        await testUtils.nextTick();

        assert.containsOnce($('body'), '.o_translation_dialog');
        assert.containsN($('.o_translation_dialog'), '.translation>input.o_field_char', 2,
            'modal should have 2 languages to translate');

        _t.database.multi_lang = multiLang;
        list.destroy();
    });

    QUnit.test('long words in text cells should break into smaller lines', async function (assert) {
        assert.expect(2);

        this.data.foo.records[0].text = "a";
        this.data.foo.records[1].text = "pneumonoultramicroscopicsilicovolcanoconiosis"; // longest english word I could find

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="text"/></tree>',
        });

        // Intentionally set the table width to a small size
        list.$('table').width('100px');
        list.$('th:last').width('100px');
        var shortText = list.$('.o_data_row:eq(0) td:last')[0].clientHeight;
        var longText = list.$('.o_data_row:eq(1) td:last')[0].clientHeight;
        var emptyText = list.$('.o_data_row:eq(2) td:last')[0].clientHeight;

        assert.strictEqual(shortText, emptyText,
            "Short word should not change the height of the cell");
        assert.ok(longText > emptyText,
            "Long word should change the height of the cell");

        list.destroy();
    });

    QUnit.test('deleting one record', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasActionMenus: true},
            arch: '<tree><field name="foo"/></tree>',
        });


        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "should have 4 records");

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Delete");
        assert.hasClass($('body'),'modal-open', 'body should have modal-open clsss');

        await testUtils.dom.click($('body .modal button span:contains(Ok)'));

        assert.containsN(list, 'tbody td.o_list_record_selector', 3, "should have 3 records");
        list.destroy();
    });

    QUnit.test('delete all records matching the domain', async function (assert) {
        assert.expect(6);

        this.data.foo.records.push({id: 5, bar: true, foo: "xxx"});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [['bar', '=', true]],
            mockRPC: function (route, args) {
                if (args.method === 'unlink') {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
                return this._super.apply(this, arguments);
            },
            services: {
                notification: NotificationService.extend({
                    notify: function () {
                        throw new Error('should not display a notification');
                    },
                }),
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });

        assert.containsNone(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, 'tbody td.o_list_record_selector', 2, "should have 2 records");

        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        assert.containsOnce(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsOnce(list, '.o_list_selection_box .o_list_select_domain');

        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Delete");

        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        list.destroy();
    });

    QUnit.test('delete all records matching the domain (limit reached)', async function (assert) {
        assert.expect(8);

        this.data.foo.records.push({id: 5, bar: true, foo: "xxx"});
        this.data.foo.records.push({id: 6, bar: true, foo: "yyy"});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [['bar', '=', true]],
            mockRPC: function (route, args) {
                if (args.method === 'unlink') {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
                return this._super.apply(this, arguments);
            },
            services: {
                notification: NotificationService.extend({
                    notify: function () {
                        assert.step('notify');
                    },
                }),
            },
            session: {
                active_ids_limit: 4,
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });


        assert.containsNone(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, 'tbody td.o_list_record_selector', 2, "should have 2 records");

        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        assert.containsOnce(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsOnce(list, '.o_list_selection_box .o_list_select_domain');

        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Delete");

        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        assert.verifySteps(['notify']);

        list.destroy();
    });

    QUnit.test('archiving one record', async function (assert) {
        assert.expect(12);

        // add active field on foo model and make all records active
        this.data.foo.fields.active = {string: 'Active', type: 'boolean', default: true};

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasActionMenus: true},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                if (route === '/web/dataset/call_kw/foo/action_archive') {
                    this.data.foo.records[0].active = false;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });


        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "should have 4 records");

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');

        assert.verifySteps(['/web/dataset/search_read']);
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Archive");
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-secondary'));
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "still should have 4 records");

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Archive");
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-primary'));
        assert.containsN(list, 'tbody td.o_list_record_selector', 3, "should have 3 records");
        assert.verifySteps(['/web/dataset/call_kw/foo/action_archive', '/web/dataset/search_read']);
        list.destroy();
    });

    QUnit.test('archive all records matching the domain', async function (assert) {
        assert.expect(6);

        // add active field on foo model and make all records active
        this.data.foo.fields.active = {string: 'Active', type: 'boolean', default: true};
        this.data.foo.records.push({id: 5, bar: true, foo: "xxx"});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [['bar', '=', true]],
            mockRPC: function (route, args) {
                if (args.method === 'action_archive') {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            services: {
                notification: NotificationService.extend({
                    notify: function () {
                        throw new Error('should not display a notification');
                    },
                }),
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });

        assert.containsNone(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, 'tbody td.o_list_record_selector', 2, "should have 2 records");

        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        assert.containsOnce(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsOnce(list, '.o_list_selection_box .o_list_select_domain');

        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Archive");

        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        list.destroy();
    });

    QUnit.test('archive all records matching the domain (limit reached)', async function (assert) {
        assert.expect(8);

        // add active field on foo model and make all records active
        this.data.foo.fields.active = {string: 'Active', type: 'boolean', default: true};
        this.data.foo.records.push({id: 5, bar: true, foo: "xxx"});
        this.data.foo.records.push({id: 6, bar: true, foo: "yyy"});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [['bar', '=', true]],
            mockRPC: function (route, args) {
                if (args.method === 'action_archive') {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            services: {
                notification: NotificationService.extend({
                    notify: function () {
                        assert.step('notify');
                    },
                }),
            },
            session: {
                active_ids_limit: 4,
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });


        assert.containsNone(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, 'tbody td.o_list_record_selector', 2, "should have 2 records");

        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        assert.containsOnce(list, 'div.o_control_panel .o_cp_action_menus');
        assert.containsOnce(list, '.o_list_selection_box .o_list_select_domain');

        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Archive");

        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        assert.verifySteps(['notify']);

        list.destroy();
    });

    QUnit.test('pager (ungrouped and grouped mode), default limit', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.limit, 80, "default limit should be 80 in List");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_pager');
        assert.strictEqual(cpHelpers.getPagerSize(list), "4", "pager's size should be 4");
        await list.update({ groupBy: ['bar']});
        assert.strictEqual(cpHelpers.getPagerSize(list), "2", "pager's size should be 2");
        list.destroy();
    });

    QUnit.test('can sort records when clicking on header', async function (assert) {
        assert.expect(9);

        this.data.foo.fields.foo.sortable = true;

        var nbSearchRead = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route) {
                if (route === '/web/dataset/search_read') {
                    nbSearchRead++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(yop)').length,
            "record 1 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(blip)').length,
            "record 3 should be first");

        nbSearchRead = 0;
        await testUtils.dom.click(list.$('thead th:contains(Foo)'));
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        nbSearchRead = 0;
        await testUtils.dom.click(list.$('thead th:contains(Foo)'));
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(yop)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(blip)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('do not sort records when clicking on header with nolabel', async function (assert) {
        assert.expect(6);

        this.data.foo.fields.foo.sortable = true;

        let nbSearchRead = 0;
        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" nolabel="1"/><field name="int_field"/></tree>',
            mockRPC: function (route) {
                if (route === '/web/dataset/search_read') {
                    nbSearchRead++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.strictEqual(list.$('.o_data_cell').text(), "yop10blip9gnap17blip-4");

        await testUtils.dom.click(list.$('thead th[data-name="int_field"]'));
        assert.strictEqual(nbSearchRead, 2, "should have done one other search_read");
        assert.strictEqual(list.$('.o_data_cell').text(), "blip-4blip9yop10gnap17");

        await testUtils.dom.click(list.$('thead th[data-name="foo"]'));
        assert.strictEqual(nbSearchRead, 2, "shouldn't have done anymore search_read");
        assert.strictEqual(list.$('.o_data_cell').text(), "blip-4blip9yop10gnap17");

        list.destroy();
    });

    QUnit.test('use default_order', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree default_order="foo"><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.sort, 'foo ASC',
                        "should correctly set the sort attribute");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('use more complex default_order', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree default_order="foo, bar desc, int_field">' +
                    '<field name="foo"/><field name="bar"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.sort, 'foo ASC, bar DESC, int_field ASC',
                        "should correctly set the sort attribute");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on save', async function (assert) {
        assert.expect(8);

        this.data.foo.records[0].o2m = [1, 3];

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom" default_order="display_name">' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput($o2m.find('.o_field_widget'), "Value 2");
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        await testUtils.form.clickSave(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 2)').length,
            "Value 2 should be second (should be sorted after saving)");
        assert.ok(form.$('tbody tr:eq(2) td:contains(Value 3)').length,
            "Value 3 should be third");

        form.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on demand', async function (assert) {
        assert.expect(11);

        this.data.foo.records[0].o2m = [1, 3];
        this.data.bar.fields = {name: {string: "Name", type: "char", sortable: true}};
        this.data.bar.records[0].name = "Value 1";
        this.data.bar.records[2].name = "Value 3";

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom" default_order="name">' +
                                '<field name="name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput($o2m.find('.o_field_widget'), "Value 2");
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        await testUtils.dom.click(form.$('.o_form_sheet_bg'));

        await testUtils.dom.click($o2m.find('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 1',
            "Value 1 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 3',
            "Value 3 should be third");

        await testUtils.dom.click($o2m.find('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 3',
            "Value 3 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 1',
            "Value 1 should be third");

        form.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on demand in page', async function (assert) {
        assert.expect(4);

        this.data.bar.fields = {name: {string: "Name", type: "char", sortable: true}};

        var ids = [];
        for (var i=0; i<45; i++) {
            var id = 4 + i;
            ids.push(id);
            this.data.bar.records.push({
                id: id,
                name: "Value " + (id < 10 ? '0' : '') + id,
            });
        }
        this.data.foo.records[0].o2m = ids;

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom" default_order="name">' +
                                '<field name="name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        await cpHelpers.pagerNext('.o_field_widget[name=o2m]');
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 44',
            "record 44 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 48',
            "record 48 should be last");

        await testUtils.dom.click(form.$('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 08',
            "record 48 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 04',
            "record 44 should be first");

        form.destroy();
    });

    QUnit.test('can display button in edit mode', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="notafield" type="object" icon="fa-asterisk" class="o_yeah"/>' +
                '</tree>',
        });
        assert.containsN(list, 'tbody button[name=notafield]', 4);
        assert.containsN(list, 'tbody button[name=notafield].o_yeah', 4, "class o_yeah should be set on the four button");
        list.destroy();
    });

    QUnit.test('can display a list with a many2many field', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="m2m"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                assert.step(route);
                return this._super(route, args);
            },
        });
        assert.verifySteps(['/web/dataset/search_read'], "should have done 1 search_read");
        assert.ok(list.$('td:contains(3 records)').length,
            "should have a td with correct formatted value");
        list.destroy();
    });

    QUnit.test('list with group_by_no_leaf flag in context', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            context: {
                group_by_no_leaf: true,
            }
        });

        assert.containsNone(list, '.o_list_buttons', "should not have any buttons");
        list.destroy();
    });

    QUnit.test('display a tooltip on a field', async function (assert) {
        assert.expect(4);

        var initialDebugMode = odoo.debug;
        odoo.debug = false;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" widget="toggle_button"/>' +
                '</tree>',
        });

        // this is done to force the tooltip to show immediately instead of waiting
        // 1000 ms. not totally academic, but a short test suite is easier to sell :(
        list.$('th[data-name=foo]').tooltip('show', false);

        list.$('th[data-name=foo]').trigger($.Event('mouseenter'));
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 0, "should not have rendered a tooltip");

        odoo.debug = true;
        // it is necessary to rerender the list so tooltips can be properly created
        await list.reload();
        list.$('th[data-name=foo]').tooltip('show', false);
        list.$('th[data-name=foo]').trigger($.Event('mouseenter'));
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 1, "should have rendered a tooltip");

        await list.reload();
        list.$('th[data-name=bar]').tooltip('show', false);
        list.$('th[data-name=bar]').trigger($.Event('mouseenter'));
        assert.containsOnce($, '.oe_tooltip_technical>li[data-item="widget"]',
            'widget should be present for this field');
        assert.strictEqual($('.oe_tooltip_technical>li[data-item="widget"]')[0].lastChild.wholeText.trim(),
            'Button (toggle_button)', "widget description should be correct");

        odoo.debug = initialDebugMode;
        list.destroy();
    });

    QUnit.test('support row decoration', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree decoration-info="int_field > 5">' +
                    '<field name="foo"/><field name="int_field"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody tr.text-info', 3,
            "should have 3 columns with text-info class");

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('support row decoration (with unset numeric values)', async function (assert) {
        assert.expect(2);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" decoration-danger="int_field &lt; 0">' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsNone(list, 'tr.o_data_row.text-danger',
            "the data row should not have .text-danger decoration (int_field is unset)");
        await testUtils.fields.editInput(list.$('input[name="int_field"]'), '-3');
        assert.containsOnce(list, 'tr.o_data_row.text-danger',
            "the data row should have .text-danger decoration (int_field is negative)");
        list.destroy();
    });

    QUnit.test('support row decoration with date', async function (assert) {
        assert.expect(3);

        this.data.foo.records[0].datetime = '2017-02-27 12:51:35';

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree decoration-info="datetime == \'2017-02-27 12:51:35\'" decoration-danger="datetime &gt; \'2017-02-27 12:51:35\' AND datetime &lt; \'2017-02-27 10:51:35\'">' +
                    '<field name="datetime"/><field name="int_field"/>' +
                '</tree>',
        });

        assert.containsOnce(list, 'tbody tr.text-info',
            "should have 1 columns with text-info class with good datetime");

        assert.containsNone(list, 'tbody tr.text-danger',
            "should have 0 columns with text-danger class with wrong timezone datetime");

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('support field decoration', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo" decoration-danger="int_field > 5"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        assert.containsN(list, 'tbody td.o_list_char.text-danger', 3);
        assert.containsNone(list, 'tbody td.o_list_number.text-danger');

        list.destroy();
    });

    QUnit.test('bounce create button when no data and click on empty area', async function (assert) {
        assert.expect(4);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a record</p>'
                }
            },
        });

        assert.containsNone(list, '.o_view_nocontent');
        await testUtils.dom.click(list.$('.o_list_view'));
        assert.doesNotHaveClass(list.$('.o_list_button_add'), 'o_catch_attention');

        await list.reload({ domain: [['id', '<', 0]] });
        assert.containsOnce(list, '.o_view_nocontent');
        await testUtils.dom.click(list.$('.o_view_nocontent'));
        assert.hasClass(list.$('.o_list_button_add'), 'o_catch_attention');
        list.destroy();
    });

    QUnit.test('no content helper when no data', async function (assert) {
        assert.expect(5);

        var records = this.data.foo.records;

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                }
            },
        });

        assert.containsOnce(list, '.o_view_nocontent',
            "should display the no content helper");

        assert.containsNone(list, 'table', "should not have a table in the dom");

        assert.strictEqual(list.$('.o_view_nocontent p.hello:contains(add a partner)').length, 1,
            "should have rendered no content helper from action");

        this.data.foo.records = records;
        await list.reload();

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");
        assert.containsOnce(list, 'table', "should have a table in the dom");
        list.destroy();
    });

    QUnit.test('no nocontent helper when no data and no help', async function (assert) {
        assert.expect(3);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");

        assert.containsNone(list, 'tr.o_data_row',
            "should not have any data row");

        assert.containsOnce(list, 'table', "should have a table in the dom");
        list.destroy();
    });

    QUnit.test("empty list with sample data", async function (assert) {
        assert.expect(19);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <field name="m2o"/>
                    <field name="m2m" widget="many2many_tags"/>
                    <field name="date"/>
                    <field name="datetime"/>
                </tree>`,
            domain: [['id', '<', 0]], // such that no record matches the domain
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                }
            },
        });

        assert.hasClass(list.$el, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 10);
        assert.containsOnce(list, '.o_nocontent_help .hello');

        // Check list sample data
        const firstRow = list.el.querySelector('.o_data_row');
        const cells = firstRow.querySelectorAll(':scope > .o_data_cell');
        assert.strictEqual(cells[0].innerText.trim(), "",
            "Char field should yield an empty element"
        );
        assert.containsOnce(cells[1], '.custom-checkbox',
            "Boolean field has been instantiated"
        );
        assert.notOk(isNaN(cells[2].innerText.trim()), "Intger value is a number");
        assert.ok(cells[3].innerText.trim(), "Many2one field is a string");

        const firstM2MTag = cells[4].querySelector(
            ':scope span.o_badge_text'
        ).innerText.trim();
        assert.ok(firstM2MTag.length > 0, "Many2many contains at least one string tag");

        assert.ok(/\d{2}\/\d{2}\/\d{4}/.test(cells[5].innerText.trim()),
            "Date field should have the right format"
        );
        assert.ok(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}/.test(cells[6].innerText.trim()),
            "Datetime field should have the right format"
        );

        const textContent = list.$el.text();
        await list.reload();
        assert.strictEqual(textContent, list.$el.text(),
            'The content should be the same after reloading the view without change'
        );

        // reload with another domain -> should no longer display the sample records
        await list.reload({ domain: Domain.FALSE_DOMAIN });

        assert.doesNotHaveClass(list.$el, 'o_view_sample_data');
        assert.containsNone(list, '.o_list_table');
        assert.containsOnce(list, '.o_nocontent_help .hello');

        // reload with another domain matching records
        await list.reload({ domain: Domain.TRUE_DOMAIN });

        assert.doesNotHaveClass(list.$el, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 4);
        assert.containsNone(list, '.o_nocontent_help .hello');

        list.destroy();
    });

    QUnit.test("empty list with sample data: toggle optional field", async function (assert) {
        assert.expect(9);

        const RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="m2o" optional="hide"/>
                </tree>`,
            domain: Domain.FALSE_DOMAIN,
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.hasClass(list.$el, 'o_view_sample_data');
        assert.ok(list.$('.o_data_row').length > 0);
        assert.hasClass(list.el.querySelector('.o_data_row'), 'o_sample_data_disabled');
        assert.containsN(list, 'th', 2, "should have 2 th, 1 for selector and 1 for foo");
        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle');

        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));

        assert.hasClass(list.$el, 'o_view_sample_data');
        assert.ok(list.$('.o_data_row').length > 0);
        assert.hasClass(list.el.querySelector('.o_data_row'), 'o_sample_data_disabled');
        assert.containsN(list, 'th', 3);

        list.destroy();
    });

    QUnit.test("empty list with sample data: keyboard navigation", async function (assert) {
        assert.expect(11);

        const list = await createView({
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            data: this.data,
            domain: Domain.FALSE_DOMAIN,
            model: 'foo',
            View: ListView,
        });

        // Check keynav is disabled
        assert.hasClass(
            list.el.querySelector('.o_data_row'),
            'o_sample_data_disabled'
        );
        assert.hasClass(
            list.el.querySelector('.o_list_table > tfoot'),
            'o_sample_data_disabled'
        );
        assert.hasClass(
            list.el.querySelector('.o_list_table > thead .o_list_record_selector'),
            'o_sample_data_disabled'
        );
        assert.containsNone(list.renderer, 'input:not([tabindex="-1"])');

        // From search bar
        assert.hasClass(document.activeElement, 'o_searchview_input');

        await testUtils.fields.triggerKeydown(document.activeElement, 'down');

        assert.hasClass(document.activeElement, 'o_searchview_input');

        // From 'Create' button
        document.querySelector('.btn.o_list_button_add').focus();

        assert.hasClass(document.activeElement, 'o_list_button_add');

        await testUtils.fields.triggerKeydown(document.activeElement, 'down');

        assert.hasClass(document.activeElement, 'o_list_button_add');

        await testUtils.fields.triggerKeydown(document.activeElement, 'tab');

        assert.containsNone(document.body, '.oe_tooltip_string');

        // From column header
        list.el.querySelector(':scope th[data-name="foo"]').focus();

        assert.ok(document.activeElement.dataset.name === 'foo');

        await testUtils.fields.triggerKeydown(document.activeElement, 'down');

        assert.ok(document.activeElement.dataset.name === 'foo');

        list.destroy();
    });

    QUnit.test("non empty list with sample data", async function (assert) {
        assert.expect(6);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            domain: Domain.TRUE_DOMAIN,
        });

        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 4);
        assert.doesNotHaveClass(list.$el, 'o_view_sample_data');

        // reload with another domain matching no record (should not display the sample records)
        await list.reload({ domain: Domain.FALSE_DOMAIN });

        assert.containsOnce(list, '.o_list_table');
        assert.containsNone(list, '.o_data_row');
        assert.doesNotHaveClass(list.$el, 'o_view_sample_data');

        list.destroy();
    });

    QUnit.test('click on header in empty list with sample data', async function (assert) {
        assert.expect(4);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            domain: Domain.FALSE_DOMAIN,
        });

        assert.hasClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 10);

        const content = list.$el.text();
        await testUtils.dom.click(list.$('tr:first .o_column_sortable:first'));
        assert.strictEqual(list.$el.text(), content, "the content should still be the same");

        list.destroy();
    });

    QUnit.test("non empty editable list with sample data: delete all records", async function (assert) {
        assert.expect(7);

        const list = await createView({
            arch: `
                <tree editable="top" sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            data: this.data,
            domain: Domain.TRUE_DOMAIN,
            model: 'foo',
            View: ListView,
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                },
                hasActionMenus: true,
            },
        });

        // Initial state: all records displayed
        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 4);
        assert.containsNone(list, '.o_nocontent_help');

        // Delete all records
        await testUtils.dom.click(list.el.querySelector('thead .o_list_record_selector input'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Delete");
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        // Final state: no more sample data, but nocontent helper displayed
        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsNone(list, '.o_list_table');
        assert.containsOnce(list, '.o_nocontent_help');

        list.destroy();
    });

    QUnit.test("empty editable list with sample data: start create record and cancel", async function (assert) {
        assert.expect(10);

        const list = await createView({
            arch: `
                <tree editable="top" sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            data: this.data,
            domain: Domain.FALSE_DOMAIN,
            model: 'foo',
            View: ListView,
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                },
            },
        });

        // Initial state: sample data and nocontent helper displayed
        assert.hasClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 10);
        assert.containsOnce(list, '.o_nocontent_help');

        // Start creating a record
        await testUtils.dom.click(list.el.querySelector('.btn.o_list_button_add'));

        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_data_row');

        // Discard temporary record
        await testUtils.dom.click(list.el.querySelector('.btn.o_list_button_discard'));

        // Final state: table should be displayed with no data at all
        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsNone(list, '.o_data_row');
        assert.containsNone(list, '.o_nocontent_help');

        list.destroy();
    });

    QUnit.test("empty editable list with sample data: create and delete record", async function (assert) {
        assert.expect(13);

        const list = await createView({
            arch: `
                <tree editable="top" sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            data: this.data,
            domain: Domain.FALSE_DOMAIN,
            model: 'foo',
            View: ListView,
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                },
                hasActionMenus: true,
            },
        });

        // Initial state: sample data and nocontent helper displayed
        assert.hasClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsN(list, '.o_data_row', 10);
        assert.containsOnce(list, '.o_nocontent_help');

        // Start creating a record
        await testUtils.dom.click(list.el.querySelector('.btn.o_list_button_add'));

        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_data_row');

        // Save temporary record
        await testUtils.dom.click(list.el.querySelector('.btn.o_list_button_save'));

        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsOnce(list, '.o_list_table');
        assert.containsOnce(list, '.o_data_row');
        assert.containsNone(list, '.o_nocontent_help');

        // Delete newly created record
        await testUtils.dom.click(list.el.querySelector('.o_data_row input'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Delete");
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        // Final state: there should be no table, but the no content helper
        assert.doesNotHaveClass(list, 'o_view_sample_data');
        assert.containsNone(list, '.o_list_table');
        assert.containsOnce(list, '.o_nocontent_help');
        list.destroy();
    });

    QUnit.test('Do not display nocontent when it is an empty html tag', async function (assert) {
        assert.expect(2);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                action: {
                    help: '<p class="hello"></p>'
                }
            },
        });

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");

        assert.containsOnce(list, 'table', "should have a table in the dom");

        list.destroy();
    });

    QUnit.test('groupby node with a button', async function (assert) {
        assert.expect(14);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<button string="Button 1" type="object" name="button_method"/>' +
                '</groupby>' +
            '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (ev) {
                    assert.deepEqual(ev.data.env.currentID, 2,
                        'should call with correct id');
                    assert.strictEqual(ev.data.env.model, 'res_currency',
                        'should call with correct model');
                    assert.strictEqual(ev.data.action_data.name, 'button_method',
                        "should call correct method");
                    assert.strictEqual(ev.data.action_data.type, 'object',
                        'should have correct type');
                    ev.data.on_success();
                },
            },
        });

        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsOnce(list, 'thead th:not(.o_list_record_selector)',
            "there should be only one column");

        await list.update({groupBy: ['currency_id']});

        assert.verifySteps(['web_read_group']);
        assert.containsN(list, '.o_group_header', 2,
            "there should be 2 group headers");
        assert.containsNone(list, '.o_group_header button', 0,
            "there should be no button in the header");

        await testUtils.dom.click(list.$('.o_group_header:eq(0)'));
        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsOnce(list, '.o_group_header button');

        await testUtils.dom.click(list.$('.o_group_header:eq(0) button'));

        list.destroy();
    });

    QUnit.test('groupby node with a button in inner groupbys', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<button string="Button 1" type="object" name="button_method"/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['bar', 'currency_id'],
        });

        assert.containsN(list, '.o_group_header', 2,
            "there should be 2 group headers");
        assert.containsNone(list, '.o_group_header button',
            "there should be no button in the header");

        await testUtils.dom.click(list.$('.o_group_header:eq(0)'));

        assert.containsN(list, 'tbody:eq(1) .o_group_header', 2,
            "there should be 2 inner groups header");
        assert.containsNone(list, 'tbody:eq(1) .o_group_header button',
            "there should be no button in the header");

        await testUtils.dom.click(list.$('tbody:eq(1) .o_group_header:eq(0)'));

        assert.containsOnce(list, '.o_group_header button',
            "there should be one button in the header");

        list.destroy();
    });

    QUnit.test('groupby node with a button with modifiers', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<field name="position"/>' +
                    '<button string="Button 1" type="object" name="button_method" attrs=\'{"invisible": [("position", "=", "after")]}\'/>' +
                '</groupby>' +
            '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read' && args.model === 'res_currency') {
                    assert.deepEqual(args.args, [[2, 1], ['position']]);
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['currency_id'],
        });

        assert.verifySteps(['web_read_group', 'read']);

        await testUtils.dom.click(list.$('.o_group_header:eq(0)'));

        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsOnce(list, '.o_group_header button.o_invisible_modifier',
            "the first group (EUR) should have an invisible button");

        await testUtils.dom.click(list.$('.o_group_header:eq(1)'));

        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsN(list, '.o_group_header button', 2,
            "there should be two buttons (one by header)");
        assert.doesNotHaveClass(list, '.o_group_header:eq(1) button', 'o_invisible_modifier',
            "the second header button should be visible");

        list.destroy();
    });

    QUnit.test('reload list view with groupby node', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1">' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<field name="position"/>' +
                    '<button string="Button 1" type="object" name="button_method" attrs=\'{"invisible": [("position", "=", "after")]}\'/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['currency_id'],
        });

        assert.containsOnce(list, '.o_group_header button:not(.o_invisible_modifier)',
            "there should be one visible button");

        await list.reload({ domain: [] });
        assert.containsOnce(list, '.o_group_header button:not(.o_invisible_modifier)',
            "there should still be one visible button");

        list.destroy();
    });

    QUnit.test('editable list view with groupby node and modifiers', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1" editable="bottom">' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<field name="position"/>' +
                    '<button string="Button 1" type="object" name="button_method" attrs=\'{"invisible": [("position", "=", "after")]}\'/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['currency_id'],
        });

        assert.doesNotHaveClass(list.$('.o_data_row:first'), 'o_selected_row',
            "first row should be in readonly mode");

        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell'));
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row',
            "the row should be in edit mode");

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');
        assert.doesNotHaveClass(list.$('.o_data_row:first'), 'o_selected_row',
            "the row should be back in readonly mode");

        list.destroy();
    });

    QUnit.test('groupby node with edit button', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1">' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<button string="Button 1" type="edit" name="edit"/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['currency_id'],
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action, {
                        context: {create: false},
                        res_id: 2,
                        res_model: 'res_currency',
                        type: 'ir.actions.act_window',
                        views: [[false, 'form']],
                        flags: {mode: 'edit'},
                    }, "should trigger do_action with correct action parameter");
                }
            },
        });
        await testUtils.dom.click(list.$('.o_group_header:eq(0) button'));
        list.destroy();
    });

    QUnit.test('groupby node with subfields, and onchange', async function (assert) {
        assert.expect(1);

        this.data.foo.onchanges = {
            foo: function () {},
        };

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `<tree editable="bottom" expand="1">
                    <field name="foo"/>
                    <field name="currency_id"/>
                    <groupby name="currency_id">
                        <field name="position" invisible="1"/>
                    </groupby>
                </tree>`,
            groupBy: ['currency_id'],
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.deepEqual(args.args[3], {
                        foo: "1",
                        currency_id: "",
                    }, 'onchange spec should not follow relation of many2one fields');
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:first'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), "new value");

        list.destroy();
    });

    QUnit.test('list view, editable, without data', async function (assert) {
        assert.expect(12);

        this.data.foo.records = [];

        this.data.foo.fields.date.default = "2017-02-10";

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="date"/>' +
                    '<field name="m2o"/>' +
                    '<field name="foo"/>' +
                    '<button type="object" icon="fa-plus-square" name="method"/>' +
                '</tree>',
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                }
            },
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.ok(true, "should have created a record");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(list, '.o_view_nocontent',
            "should have a no content helper displayed");

        assert.containsNone(list, 'div.table-responsive',
            "should not have a div.table-responsive");
        assert.containsNone(list, 'table', "should not have rendered a table");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsNone(list, '.o_view_nocontent',
            "should not have a no content helper displayed");
        assert.containsOnce(list, 'table', "should have rendered a table");

        assert.hasClass(list.$('tbody tr:eq(0)'), 'o_selected_row',
            "the date field td should be in edit mode");
        assert.strictEqual(list.$('tbody tr:eq(0) td:eq(1)').text().trim(), "",
            "the date field td should not have any content");

        assert.strictEqual(list.$('tr.o_selected_row .o_list_record_selector input').prop('disabled'), true,
            "record selector checkbox should be disabled while the record is not yet created");
        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), true,
            "buttons should be disabled while the record is not yet created");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(list.$('tbody tr:eq(0) .o_list_record_selector input').prop('disabled'), false,
            "record selector checkbox should not be disabled once the record is created");
        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), false,
            "buttons should not be disabled once the record is created");

        list.destroy();
    });

    QUnit.test('list view, editable, with a button', async function (assert) {
        assert.expect(1);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                    '<button string="abc" icon="fa-phone" type="object" name="schedule_another_phonecall"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsOnce(list, 'table button.o_icon_button i.fa-phone',
            "should have rendered a button");
        list.destroy();
    });

    QUnit.test('list view with a button without icon', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                    '<button string="abc" type="object" name="schedule_another_phonecall"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('table button').first().text(), 'abc',
            "should have rendered a button with string attribute as label");
        list.destroy();
    });

    QUnit.test('list view, editable, can discard', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 0, "no input should be in the table");

        await testUtils.dom.click(list.$('tbody td:not(.o_list_record_selector):first'));
        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 1, "first cell should be editable");

        assert.ok(list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should be visible");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 0, "no input should be in the table");

        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should not be visible");
        list.destroy();
    });

    QUnit.test('editable list view, click on the list to save', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.date.default = "2017-02-10";
        this.data.foo.records = [];

        var createCount = 0;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    createCount++;
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.click(list.$('.o_list_view'));

        assert.strictEqual(createCount, 1, "should have created a record");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.click(list.$('tfoot'));

        assert.strictEqual(createCount, 2, "should have created a record");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.click(list.$('tbody tr').last());

        assert.strictEqual(createCount, 3, "should have created a record");
        list.destroy();
    });

    QUnit.test('click on a button in a list view', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<button string="a button" name="button_action" icon="fa-car" type="object"/>' +
                '</tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    assert.deepEqual(event.data.env.currentID, 1,
                        'should call with correct id');
                    assert.strictEqual(event.data.env.model, 'foo',
                        'should call with correct model');
                    assert.strictEqual(event.data.action_data.name, 'button_action',
                        "should call correct method");
                    assert.strictEqual(event.data.action_data.type, 'object',
                        'should have correct type');
                    event.data.on_closed();
                },
            },
        });

        assert.containsN(list, 'tbody .o_list_button', 4,
            "there should be one button per row");
        assert.containsOnce(list, 'tbody .o_list_button:first .o_icon_button .fa.fa-car',
            'buttons should have correct icon');

        await testUtils.dom.click(list.$('tbody .o_list_button:first > button'));
        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/search_read'],
            "should have reloaded the view (after the action is complete)");
        list.destroy();
    });

    QUnit.test('invisible attrs in readonly and editable list', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<button string="a button" name="button_action" icon="fa-car" ' +
                        'type="object" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="foo" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                '</tree>',
        });

        assert.equal(list.$('tbody tr:nth(0) td:nth(4)').html(), "",
            "td that contains an invisible field should be empty");
        assert.hasClass(list.$('tbody tr:nth(0) td:nth(1) button'), "o_invisible_modifier",
            "button with invisible attrs should be properly hidden");

        // edit first row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2)'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(4) input.o_invisible_modifier').length, 1,
            "td that contains an invisible field should not be empty in edition");
        assert.hasClass(list.$('tbody tr:nth(0) td:nth(1) button'), "o_invisible_modifier",
            "button with invisible attrs should be properly hidden");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        // click on the invisible field's cell to edit first row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(4)'));
        assert.hasClass(list.$('tbody tr:nth(0)'),'o_selected_row',
            "first row should be in edition");
        list.destroy();
    });

    QUnit.test('monetary fields are properly rendered', async function (assert) {
        assert.expect(3);

        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="id"/>' +
                    '<field name="amount"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                '</tree>',
            session: {
                currencies: currencies,
            },
        });

        assert.containsN(list, 'tbody tr:first td', 3,
            "currency_id column should not be in the table");
        assert.strictEqual(list.$('tbody tr:first td:nth(2)').text().replace(/\s/g, ' '),
            '1200.00 €', "currency_id column should not be in the table");
        assert.strictEqual(list.$('tbody tr:nth(1) td:nth(2)').text().replace(/\s/g, ' '),
            '$ 500.00', "currency_id column should not be in the table");

        list.destroy();
    });

    QUnit.test('simple list with date and datetime', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="date"/><field name="datetime"/></tree>',
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        assert.strictEqual(list.$('td:eq(1)').text(), "01/25/2017",
            "should have formatted the date");
        assert.strictEqual(list.$('td:eq(2)').text(), "12/12/2016 12:55:05",
            "should have formatted the datetime");
        list.destroy();
    });

    QUnit.test('edit a row by clicking on a readonly field', async function (assert) {
        assert.expect(9);

        this.data.foo.fields.foo.readonly = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.hasClass(list.$('.o_data_row:first td:nth(1)'),'o_readonly_modifier',
            "foo field cells should have class 'o_readonly_modifier'");

        // edit the first row
        await testUtils.dom.click(list.$('.o_data_row:first td:nth(1)'));
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should be selected");
        var $cell = list.$('.o_data_row:first td:nth(1)');
        // review
        assert.hasClass($cell, 'o_readonly_modifier');
        assert.hasClass($cell.parent(),'o_selected_row');
        assert.strictEqual(list.$('.o_data_row:first td:nth(1) span').text(), 'yop',
            "a widget should have been rendered for readonly fields");
        assert.hasClass(list.$('.o_data_row:first td:nth(2)').parent(),'o_selected_row',
            "field 'int_field' should be in edition");
        assert.strictEqual(list.$('.o_data_row:first td:nth(2) input').length, 1,
            "a widget for field 'int_field should have been rendered'");

        // click again on readonly cell of first line: nothing should have changed
        await testUtils.dom.click(list.$('.o_data_row:first td:nth(1)'));
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should be selected");
        assert.strictEqual(list.$('.o_data_row:first td:nth(2) input').length, 1,
            "a widget for field 'int_field' should have been rendered (only once)");

        list.destroy();
    });

    QUnit.test('list view with nested groups', async function (assert) {
        assert.expect(42);

        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 2});

        var nbRPCs = {readGroup: 0, searchRead: 0};
        var envIDs = []; // the ids that should be in the environment during this test

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ['m2o', 'foo'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    if (args.kwargs.groupby[0] === 'foo') { // nested read_group
                        // called twice (once when opening the group, once when sorting)
                        assert.deepEqual(args.kwargs.domain, [['m2o', '=', 1]],
                            "nested read_group should be called with correct domain");
                    }
                    nbRPCs.readGroup++;
                } else if (route === '/web/dataset/search_read') {
                    // called twice (once when opening the group, once when sorting)
                    assert.deepEqual(args.domain, [['foo', '=', 'blip'], ['m2o', '=', 1]],
                        "nested search_read should be called with correct domain");
                    nbRPCs.searchRead++;
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.res_id, 4,
                        "'switch_view' event has been triggered");
                },
            },
        });

        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        // basic rendering tests
        assert.containsOnce(list, 'tbody', "there should be 1 tbody");
        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");
        assert.strictEqual(list.$('.o_group_name:first').text(), 'Value 1 (4)',
            "group should have correct name and count");
        assert.containsN(list, '.o_group_name .fa-caret-right', 2,
            "the carret of closed groups should be right");
        assert.strictEqual(list.$('.o_group_name:first span').css('padding-left'),
            '2px', "groups of level 1 should have a 2px padding-left");
        assert.strictEqual(list.$('.o_group_header:first td:last').text(), '16',
            "group aggregates are correctly displayed");

        // open the first group
        nbRPCs = {readGroup: 0, searchRead: 0};
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        var $openGroup = list.$('tbody:nth(1)');
        assert.strictEqual(list.$('.o_group_name:first').text(), 'Value 1 (4)',
            "group should have correct name and count (of records, not inner subgroups)");
        assert.containsN(list, 'tbody', 3, "there should be 3 tbodys");
        assert.containsOnce(list, '.o_group_name:first .fa-caret-down',
            "the carret of open groups should be down");
        assert.strictEqual($openGroup.find('.o_group_header').length, 3,
            "open group should contain 3 groups");
        assert.strictEqual($openGroup.find('.o_group_name:nth(2)').text(), 'blip (2)',
            "group should have correct name and count");
        assert.strictEqual($openGroup.find('.o_group_name:nth(2) span').css('padding-left'),
            '22px', "groups of level 2 should have a 22px padding-left");
        assert.strictEqual($openGroup.find('.o_group_header:nth(2) td:last').text(), '-11',
            "inner group aggregates are correctly displayed");

        // open subgroup
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = [4, 5]; // the opened subgroup contains these two records
        await testUtils.dom.click($openGroup.find('.o_group_header:nth(2)'));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        var $openSubGroup = list.$('tbody:nth(2)');
        assert.containsN(list, 'tbody', 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-4',
            "first record in open subgroup should be res_id 4 (with int_field -4)");

        // open a record (should trigger event 'open_record')
        await testUtils.dom.click($openSubGroup.find('.o_data_row:first'));

        // sort by int_field (ASC) and check that open groups are still open
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = [5, 4]; // order of the records changed
        await testUtils.dom.click(list.$('thead th:last'));
        assert.strictEqual(nbRPCs.readGroup, 2, "should have done two read_groups");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        $openSubGroup = list.$('tbody:nth(2)');
        assert.containsN(list, 'tbody', 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-7',
            "first record in open subgroup should be res_id 5 (with int_field -7)");

        // close first level group
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = []; // the group being closed, there is no more record in the environment
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        assert.containsOnce(list, 'tbody', "there should be 1 tbody");
        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");
        assert.containsN(list, '.o_group_name .fa-caret-right', 2,
            "the carret of closed groups should be right");

        list.destroy();
    });

    QUnit.test('grouped list on selection field at level 2', async function (assert) {
        assert.expect(4);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ['m2o', 'priority'],
        });

        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");

        // open the first group
        await testUtils.dom.click(list.$('.o_group_header:first'));

        var $openGroup = list.$('tbody:nth(1)');
        assert.strictEqual($openGroup.find('tr').length, 3,
            "should have 3 subgroups");
        assert.strictEqual($openGroup.find('tr').length, 3,
            "should have 3 subgroups");
        assert.strictEqual($openGroup.find('.o_group_name:first').text(), 'Low (3)',
            "should display the selection name in the group header");

        list.destroy();
    });

    QUnit.test('grouped list with a pager in a group', async function (assert) {
        assert.expect(6);
        this.data.foo.records[3].bar = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            viewOptions: {
                limit: 3,
            },
        });
        var headerHeight = list.$('.o_group_header').css('height');

        // basic rendering checks
        await testUtils.dom.click(list.$('.o_group_header'));
        assert.strictEqual(list.$('.o_group_header').css('height'), headerHeight,
            "height of group header shouldn't have changed");
        assert.hasClass(list.$('.o_group_header th:eq(1) > nav'), 'o_pager',
            "last cell of open group header should have classname 'o_pager'");

        assert.strictEqual(cpHelpers.getPagerValue('.o_group_header'), '1-3',
            "pager's value should be correct");
        assert.containsN(list, '.o_data_row', 3,
            "open group should display 3 records");

        // go to next page
        await cpHelpers.pagerNext('.o_group_header');
        assert.strictEqual(cpHelpers.getPagerValue('.o_group_header'), '4-4',
            "pager's value should be correct");
        assert.containsOnce(list, '.o_data_row',
            "open group should display 1 record");

        list.destroy();
    });

    QUnit.test('edition: create new line, then discard', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, 'tr.o_data_row', 4,
            "should have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 0,
            "create button should be hidden");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 1,
            "discard button should be visible");
        assert.containsNone(list, '.o_list_record_selector input:enabled');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsN(list, 'tr.o_data_row', 4,
            "should still have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible again");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden again");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        list.destroy();
    });

    QUnit.test('invisible attrs on fields are re-evaluated on field change', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'invisible\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody td.o_invisible_modifier', 3,
            "there should be 3 invisible foo cells in readonly mode");

        // Make first line editable
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been rendered as invisible");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_invisible_modifier)').length, 1,
            "the foo field widget should have been marked as non-invisible");
        assert.containsN(list, 'tbody td.o_invisible_modifier', 2,
            "the foo field widget parent cell should not be invisible anymore");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been marked as invisible again");
        assert.containsN(list, 'tbody td.o_invisible_modifier', 3,
            "the foo field widget parent cell should now be invisible again");

        // Reswitch the cell to editable and save the row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        await testUtils.dom.click(list.$('thead'));

        assert.containsN(list, 'tbody td.o_invisible_modifier', 2,
            "there should be 2 invisible foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('readonly attrs on fields are re-evaluated on field change', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'readonly\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody td.o_readonly_modifier', 3,
            "there should be 3 readonly foo cells in readonly mode");

        // Make first line editable
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rendered as readonly");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "the foo field widget parent cell should not be readonly anymore");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as readonly");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 3,
            "the foo field widget parent cell should now be readonly again");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable again");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "the foo field widget parent cell should not be readonly again");

        // Click outside to leave edition mode
        await testUtils.dom.click(list.$el);

        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "there should be 2 readonly foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('required attrs on fields are re-evaluated on field change', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'required\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody td.o_required_modifier', 3,
            "there should be 3 required foo cells in readonly mode");

        // Make first line editable
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been rendered as required");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_required_modifier)').length, 1,
            "the foo field widget should have been marked as non-required");
        assert.containsN(list, 'tbody td.o_required_modifier', 2,
            "the foo field widget parent cell should not be required anymore");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been marked as required again");
        assert.containsN(list, 'tbody td.o_required_modifier', 3,
            "the foo field widget parent cell should now be required again");

        // Reswitch the cell to editable and save the row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        await testUtils.dom.click(list.$('thead'));

        assert.containsN(list, 'tbody td.o_required_modifier', 2,
            "there should be 2 required foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('leaving unvalid rows in edition', async function (assert) {
        assert.expect(4);

        var warnings = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="foo" required="1"/>' +
                    '<field name="bar"/>' +
                '</tree>',
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        if (params.type === 'danger') {
                            warnings++;
                        }
                    }
                }),
            },
        });

        // Start first line edition
        var $firstFooTd = list.$('tbody tr:nth(0) td:nth(1)');
        await testUtils.dom.click($firstFooTd);

        // Remove required foo field value
        await testUtils.fields.editInput($firstFooTd.find('input'), "");

        // Try starting other line edition
        var $secondFooTd = list.$('tbody tr:nth(1) td:nth(1)');
        await testUtils.dom.click($secondFooTd);
        await testUtils.nextTick();

        assert.strictEqual($firstFooTd.parent('.o_selected_row').length, 1,
            "first line should still be in edition as invalid");
        assert.containsOnce(list, 'tbody tr.o_selected_row',
            "no other line should be in edition");
        assert.strictEqual($firstFooTd.find('input.o_field_invalid').length, 1,
            "the required field should be marked as invalid");
        assert.strictEqual(warnings, 1,
            "a warning should have been displayed");

        list.destroy();
    });

    QUnit.test('open a virtual id', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'event',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
        });

        testUtils.mock.intercept(list, 'switch_view', function (event) {
            assert.deepEqual(_.pick(event.data, 'mode', 'model', 'res_id', 'view_type'), {
                mode: 'readonly',
                model: 'event',
                res_id: '2-20170808020000',
                view_type: 'form',
            }, "should trigger a switch_view event to the form view for the record virtual id");
        });
        testUtils.dom.click(list.$('td:contains(virtual)'));

        list.destroy();
    });

    QUnit.test('pressing enter on last line of editable list view', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        // click on 3rd line
        await testUtils.dom.click(list.$('td:contains(gnap)'));
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        // press enter in input
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'enter');
        assert.hasClass(list.$('tr.o_data_row:eq(3)'),'o_selected_row',
            "4rd row should be selected");
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row',
            "3rd row should no longer be selected");

        // press enter on last row
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'enter');
        assert.containsN(list, 'tr.o_data_row', 5, "should have created a 5th row");

        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/foo/onchange']);
        list.destroy();
    });

    QUnit.test('pressing tab on last cell of editable list view', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('td:contains(blip)').last());
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        //it will not create a new line unless a modification is made
        document.activeElement.value = "blip-changed";
        $(document.activeElement).trigger({type: 'change'});

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.strictEqual(document.activeElement.name, "int_field",
            "focus should be on an input with name = int_field");

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(4)'),'o_selected_row',
            "5th row should be selected");
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        assert.verifySteps(['/web/dataset/search_read',
            '/web/dataset/call_kw/foo/write',
            '/web/dataset/call_kw/foo/read',
            '/web/dataset/call_kw/foo/onchange']);
        list.destroy();
    });

    QUnit.test('navigation with tab and read completes after default_get', async function (assert) {
        assert.expect(8);

        var onchangeGetPromise = testUtils.makeTestPromise();
        var readPromise = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                var result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    return readPromise.then(function () {
                        return result;
                    });
                }
                if (args.method === 'onchange') {
                    return onchangeGetPromise.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        await testUtils.dom.click(list.$('td:contains(-4)').last());

        await testUtils.fields.editInput(list.$('tr.o_selected_row input[name="int_field"]'), '1234');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="int_field"]'), 'tab');

        onchangeGetPromise.resolve();
        assert.containsN(list, 'tbody tr.o_data_row', 4,
            "should have 4 data rows");

        readPromise.resolve();
        await testUtils.nextTick();
        assert.containsN(list, 'tbody tr.o_data_row', 5,
            "should have 5 data rows");
        assert.strictEqual(list.$('td:contains(1234)').length, 1,
            "should have a cell with new value");

        // we trigger a tab to move to the second cell in the current row. this
        // operation requires that this.currentRow is properly set in the
        // list editable renderer.
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(4)'),'o_selected_row',
            "5th row should be selected");

        assert.verifySteps(['write', 'read', 'onchange']);
        list.destroy();
    });

    QUnit.test('display toolbar', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'event',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
            toolbar: {
                action: [{
                    model_name: 'event',
                    name: 'Action event',
                    type: 'ir.actions.server',
                    usage: 'ir_actions_server',
                }],
                print: [],
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });


        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');

        await testUtils.dom.click(list.$('.o_list_record_selector:first input'));

        await cpHelpers.toggleActionMenu(list);
        assert.deepEqual(cpHelpers.getMenuItemTexts(list), ['Delete', 'Action event']);

        list.destroy();
    });

    QUnit.test('execute ActionMenus actions with correct params (single page)', async function (assert) {
        assert.expect(12);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            toolbar: {
                action: [{
                    id: 44,
                    name: 'Custom Action',
                    type: 'ir.actions.server',
                }],
                print: [],
            },
            mockRPC: function (route, args) {
                if (route === '/web/action/load') {
                    assert.step(JSON.stringify(args));
                    return Promise.resolve({});
                }
                return this._super(...arguments);
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });

        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');

        assert.containsN(list, '.o_data_row', 4);

        // select all records
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsN(list, '.o_list_record_selector input:checked', 5);

        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Custom Action");

        // unselect first record (will unselect the thead checkbox as well)
        await testUtils.dom.click(list.$('tbody .o_list_record_selector:first input'));
        assert.containsN(list, '.o_list_record_selector input:checked', 3);
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Custom Action");

        // add a domain and select first two records
        await list.reload({ domain: [['bar', '=', true]] });
        assert.containsN(list, '.o_data_row', 3);
        assert.containsNone(list, '.o_list_record_selector input:checked');

        await testUtils.dom.click(list.$('tbody .o_list_record_selector:nth(0) input'));
        await testUtils.dom.click(list.$('tbody .o_list_record_selector:nth(1) input'));
        assert.containsN(list, '.o_list_record_selector input:checked', 2);

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Custom Action");

        assert.verifySteps([
            '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}',
            '{"action_id":44,"context":{"active_id":2,"active_ids":[2,3,4],"active_model":"foo","active_domain":[]}}',
            '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2],"active_model":"foo","active_domain":[["bar","=",true]]}}',
        ]);

        list.destroy();
    });

    QUnit.test('execute ActionMenus actions with correct params (multi pages)', async function (assert) {
        assert.expect(13);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            toolbar: {
                action: [{
                    id: 44,
                    name: 'Custom Action',
                    type: 'ir.actions.server',
                }],
                print: [],
            },
            mockRPC: function (route, args) {
                if (route === '/web/action/load') {
                    assert.step(JSON.stringify(args));
                    return Promise.resolve({});
                }
                return this._super(...arguments);
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });

        assert.containsNone(list.el, 'div.o_control_panel .o_cp_action_menus');
        assert.containsN(list, '.o_data_row', 2);

        // select all records
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsN(list, '.o_list_record_selector input:checked', 3);
        assert.containsOnce(list, '.o_list_selection_box .o_list_select_domain');
        assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Custom Action");

        // select all domain
        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        assert.containsN(list, '.o_list_record_selector input:checked', 3);

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Custom Action");

        // add a domain
        await list.reload({ domain: [['bar', '=', true]] });
        assert.containsNone(list, '.o_list_selection_box .o_list_select_domain');

        // select all domain
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));
        assert.containsN(list, '.o_list_record_selector input:checked', 3);
        assert.containsNone(list, '.o_list_selection_box .o_list_select_domain');

        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Custom Action");

        assert.verifySteps([
            '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2],"active_model":"foo","active_domain":[]}}',
            '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}',
            '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2,3],"active_model":"foo","active_domain":[["bar","=",true]]}}',
        ]);

        list.destroy();
    });

    QUnit.test('edit list line after line deletion', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first());
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.ok(list.$('.o_data_row:nth(0)').is('.o_selected_row'),
            "first row should be in edition (creation)");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsNone(list, '.o_selected_row',
            "no row should be selected");
        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first());
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        assert.containsOnce(list, '.o_selected_row',
            "no other row should be selected");

        list.destroy();
    });

    QUnit.test('pressing TAB in editable list with several fields [REQUIRE FOCUS]', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:first .o_data_cell:first input')[0]);

        // // Press 'Tab' -> should go to next cell (still in first row)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:first .o_data_cell:last input')[0]);

        // // Press 'Tab' -> should go to next line (first cell)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input[name="int_field"]'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell:first input')[0]);

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with several fields [REQUIRE FOCUS]', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:nth(1)'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell:last input')[0]);

        // Press 'shift-Tab' -> should go to previous line (last cell)
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell:first input')[0]);

        // Press 'shift-Tab' -> should go to previous cell
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell:last input')[0]);

        list.destroy();
    });

    QUnit.test('navigation with tab and readonly field (no modification)', async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skip the readonly cells and
        // directly goes to the next line instead.
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
        });

        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)').last());

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        list.destroy();
    });

    QUnit.test('navigation with tab and readonly field (with modification)', async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skips the readonly cells and
        // directly goes to the next line instead.
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
        });

        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)'));

        //modity the cell content
        testUtils.fields.editAndTrigger($(document.activeElement),
            'blip-changed', ['change']);

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        list.destroy();
    });

    QUnit.test('navigation with tab on a list with create="0"', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0">' +
                        '<field name="display_name"/>' +
                    '</tree>',
        });

        assert.containsN(list, '.o_data_row', 4,
            "the list should contain 4 rows");

        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:nth(2)'),'o_selected_row',
            "third row should be in edition");

        // Press 'Tab' -> should go to next line
        // add a value in the cell because the Tab on an empty first cell would activate the next widget in the view
        await testUtils.fields.editInput(list.$('.o_selected_row input').eq(1), 11);
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input[name="display_name"]'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'),'o_selected_row',
            "fourth row should be in edition");

        // Press 'Tab' -> should go back to first line as the create action isn't available
        await testUtils.fields.editInput(list.$('.o_selected_row input').eq(1), 11);
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input[name="display_name"]'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should be in edition");

        list.destroy();
    });

    QUnit.test('navigation with tab on a one2many list with create="0"', async function (assert) {
        assert.expect(4);

        this.data.foo.records[0].o2m = [1, 2];
        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><sheet>' +
                    '<field name="o2m">' +
                        '<tree editable="bottom" create="0">' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                    '<field name="foo"/>' +
                '</sheet></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=o2m] .o_data_row', 2,
            "there should be two records in the many2many");

        await testUtils.dom.click(form.$('.o_field_widget[name=o2m] .o_data_cell:first'));
        assert.hasClass(form.$('.o_field_widget[name=o2m] .o_data_row:first'),'o_selected_row',
            "first row should be in edition");

        // Press 'Tab' -> should go to next line
        await testUtils.fields.triggerKeydown(form.$('.o_field_widget[name=o2m] .o_selected_row input'), 'tab');
        assert.hasClass(form.$('.o_field_widget[name=o2m] .o_data_row:nth(1)'),'o_selected_row',
            "second row should be in edition");

        // Press 'Tab' -> should get out of the one to many and go to the next field of the form
        await testUtils.fields.triggerKeydown(form.$('.o_field_widget[name=o2m] .o_selected_row input'), 'tab');
        // use of owlCompatibilityNextTick because the x2many control panel is updated twice
        await testUtils.owlCompatibilityNextTick();
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "the next field should be selected");

        form.destroy();
    });

    QUnit.test('edition, then navigation with tab (with a readonly field)', async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we edit and press TAB,
        // (before debounce), the save operation is properly done (before
        // selecting the next row)
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
            fieldDebounce: 1,
        });

        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)'));
        await testUtils.fields.editSelect(list.$('tr.o_selected_row input[name="foo"]'), 'new value');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.strictEqual(list.$('tbody tr:first td:contains(new value)').length, 1,
            "should have the new value visible in dom");
        assert.verifySteps(["write", "read"]);
        list.destroy();
    });

    QUnit.test('edition, then navigation with tab (with a readonly field and onchange)', async function (assert) {
        // This test makes sure that if we have a read-only cell in a row, in
        // case the keyboard navigation move over it and there a unsaved changes
        // (which will trigger an onchange), the focus of the next activable
        // field will not crash
        assert.expect(4);

        this.data.bar.onchanges = {
            o2m: function () {},
        };
        this.data.bar.fields.o2m = {string: "O2M field", type: "one2many", relation: "foo"};
        this.data.bar.records[0].o2m = [1, 4];

        var form = await createView({
            View: FormView,
            model: 'bar',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="display_name"/>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom">' +
                                '<field name="foo"/>' +
                                '<field name="date" readonly="1"/>' +
                                '<field name="int_field"/>' +
                            '</tree>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.step(args.method + ':' + args.model);
                }
                return this._super.apply(this, arguments);
            },
            fieldDebounce: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        var jq_evspecial_focus_trigger = $.event.special.focus.trigger;
        // As KeyboardEvent will be triggered by JS and not from the
        // User-Agent itself, the focus event will not trigger default
        // action (event not being trusted), we need to manually trigger
        // 'change' event on the currently focused element
        $.event.special.focus.trigger = function () {
            if (this !== document.activeElement && this.focus) {
                var activeElement = document.activeElement;
                this.focus();
                $(activeElement).trigger('change');
            }
        };

        // editable list, click on first td and press TAB
        await testUtils.dom.click(form.$('.o_data_cell:contains(yop)'));
        assert.strictEqual(document.activeElement, form.$('tr.o_selected_row input[name="foo"]')[0],
            "focus should be on an input with name = foo");
        await testUtils.fields.editInput(form.$('tr.o_selected_row input[name="foo"]'), 'new value');
        var tabEvent = $.Event("keydown", { which: $.ui.keyCode.TAB });
        await testUtils.dom.triggerEvents(form.$('tr.o_selected_row input[name="foo"]'), [tabEvent]);
        assert.strictEqual(document.activeElement, form.$('tr.o_selected_row input[name="int_field"]')[0],
            "focus should be on an input with name = int_field");

        // Restore origin jQuery special trigger for 'focus'
        $.event.special.focus.trigger = jq_evspecial_focus_trigger;

        assert.verifySteps(["onchange:bar"], "onchange method should have been called");
        form.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with a readonly field [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="qux"/>' +
                '</tree>',
        });

        // start on 'qux', line 3
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:nth(2)'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=qux]')[0]);

        // Press 'shift-Tab' -> should go to first cell (same line)
        $(document.activeElement).trigger({type: 'keydown', which: $.ui.keyCode.TAB, shiftKey: true});
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=foo]')[0]);

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with a readonly field in first column [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                '</tree>',
        });

        // start on 'foo', line 3
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:nth(1)'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=foo]')[0]);

        // Press 'shift-Tab' -> should go to previous line (last cell)
        $(document.activeElement).trigger({type: 'keydown', which: $.ui.keyCode.TAB, shiftKey: true});
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell input[name=qux]')[0]);

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with a readonly field in last column [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux" readonly="1"/>' +
                '</tree>',
        });

        // start on 'int_field', line 3
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=int_field]')[0]);

        // Press 'shift-Tab' -> should go to previous line ('foo' field)
        $(document.activeElement).trigger({type: 'keydown', which: $.ui.keyCode.TAB, shiftKey: true});
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell input[name=foo]')[0]);

        list.destroy();
    });

    QUnit.test('skip invisible fields when navigating list view with TAB', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="1"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
            res_id: 1,
        });

        await testUtils.dom.click(list.$('td:contains(gnap)'));
        assert.strictEqual(list.$('input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'tab');
        assert.strictEqual(list.$('input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('skip buttons when navigating list view with TAB (end)', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                '</tree>',
            res_id: 1,
        });

        await testUtils.dom.click(list.$('tbody tr:eq(2) td:eq(1)'));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        await testUtils.fields.triggerKeydown(list.$('tbody tr:eq(2) input[name="foo"]'), 'tab');
        assert.strictEqual(list.$('tbody tr:eq(3) input[name="foo"]')[0], document.activeElement,
            "next line should be selected");

        list.destroy();
    });

    QUnit.test('skip buttons when navigating list view with TAB (middle)', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    // Adding a button column makes conversions between column and field position trickier
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
            res_id: 1,
        });

        await testUtils.dom.click(list.$('tbody tr:eq(2) td:eq(2)'));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        await testUtils.fields.triggerKeydown(list.$('tbody tr:eq(2) input[name="foo"]'), 'tab');
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('navigation: not moving down with keydown', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        await testUtils.dom.click(list.$('td:contains(yop)'));
        assert.hasClass(list.$('tr.o_data_row:eq(0)'),'o_selected_row',
            "1st row should be selected");
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'down');
        assert.hasClass(list.$('tr.o_data_row:eq(0)'),'o_selected_row',
            "1st row should still be selected");
        list.destroy();
    });

    QUnit.test('navigation: moving right with keydown from text field does not move the focus', async function (assert) {
        assert.expect(6);

        this.data.foo.fields.foo.type = 'text';
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$('td:contains(yop)'));
        var textarea = list.$('textarea[name="foo"]')[0];
        assert.strictEqual(document.activeElement, textarea,
            "textarea should be focused");
        assert.strictEqual(textarea.selectionStart,  0,
            "textarea selection start should be at the beginning");
        assert.strictEqual(textarea.selectionEnd,  3,
            "textarea selection end should be at the end");
        textarea.selectionStart = 3; // Simulate browser keyboard right behavior (unselect)
        assert.strictEqual(document.activeElement, textarea,
            "textarea should still be focused");
        assert.ok(textarea.selectionStart === 3 && textarea.selectionEnd === 3,
            "textarea value ('yop') should not be selected and cursor should be at the end");
        await testUtils.fields.triggerKeydown($(textarea), 'right');
        assert.strictEqual(document.activeElement, list.$('textarea[name="foo"]')[0],
            "next field (checkbox) should now be focused");
        list.destroy();
    });

    QUnit.test('discarding changes in a row properly updates the rendering', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('.o_data_cell:first').text(), "yop",
            "first cell should contain 'yop'");

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('input[name="foo"]'), "hello");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.strictEqual($('.modal:visible').length, 1,
            "a modal to ask for discard should be visible");

        await testUtils.dom.click($('.modal:visible .btn-primary'));
        assert.strictEqual(list.$('.o_data_cell:first').text(), "yop",
            "first cell should still contain 'yop'");

        list.destroy();
    });

    QUnit.test('numbers in list are right-aligned', async function (assert) {
        assert.expect(2);

        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                    '<field name="amount" widget="monetary"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                '</tree>',
            session: {
                currencies: currencies,
            },
        });

        var nbCellRight = _.filter(list.$('.o_data_row:first > .o_data_cell'), function (el) {
            var style = window.getComputedStyle(el);
            return style.textAlign === 'right';
        }).length;
        assert.strictEqual(nbCellRight, 2,
            "there should be two right-aligned cells");

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        var nbInputRight = _.filter(list.$('.o_data_row:first > .o_data_cell input'), function (el) {
            var style = window.getComputedStyle(el);
            return style.textAlign === 'right';
        }).length;
        assert.strictEqual(nbInputRight, 2,
            "there should be two right-aligned input");

        list.destroy();
    });

    QUnit.test('grouped list with another grouped list parent, click unfold', async function (assert) {
        assert.expect(3);
        this.data.bar.fields = {
            cornichon: {string: 'cornichon', type: 'char'},
        };

        var rec = this.data.bar.records[0];
        // create records to have the search more button
        var newRecs = [];
        for (var i=0; i<8; i++) {
            var newRec = _.extend({}, rec);
            newRec.id = 1 + i;
            newRec.cornichon = 'extra fin';
            newRecs.push(newRec);
        }
        this.data.bar.records = newRecs;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="m2o"/></tree>',
            groupBy: ['bar'],
            archs: {
                'bar,false,list': '<tree><field name="cornichon"/></tree>',
                'bar,false,search': '<search><filter context="{\'group_by\': \'cornichon\'}" string="cornichon"/></search>',
            },
        });

        await list.update({groupBy: []});

        await testUtils.dom.clickFirst(list.$('.o_data_cell'));

        await testUtils.fields.many2one.searchAndClickItem('m2o', { item: 'Search More' });

        assert.containsOnce($('body'), '.modal-content');

        assert.containsNone($('body'), '.modal-content .o_group_name', 'list in modal not grouped');

        await testUtils.dom.click($('body .modal-content button:contains(Group By)'));

        await testUtils.dom.click($('body .modal-content .o_menu_item a:contains(cornichon)'));

        await testUtils.dom.click($('body .modal-content .o_group_header'));

        assert.containsOnce($('body'), '.modal-content .o_group_open');

        list.destroy();
    });

    QUnit.test('field values are escaped', async function (assert) {
        assert.expect(1);
        var value = '<script>throw Error();</script>';

        this.data.foo.records[0].foo = value;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('.o_data_cell:first').text(), value,
            "value should have been escaped");

        list.destroy();
    });

    QUnit.test('pressing ESC discard the current line changes', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.containsN(list, 'tr.o_data_row', 5,
            "should currently adding a 5th data row");

        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'escape');
        assert.containsN(list, 'tr.o_data_row', 4,
            "should have only 4 data row after escape");
        assert.containsNone(list, 'tr.o_data_row.o_selected_row',
            "no rows should be selected");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('pressing ESC discard the current line changes (with required)', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.containsN(list, 'tr.o_data_row', 5,
            "should currently adding a 5th data row");

        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'escape');
        assert.containsN(list, 'tr.o_data_row', 4,
            "should have only 4 data row after escape");
        assert.containsNone(list, 'tr.o_data_row.o_selected_row',
            "no rows should be selected");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('field with password attribute', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" password="True"/></tree>',
        });

        assert.strictEqual(list.$('td.o_data_cell:eq(0)').text(), '***',
            "should display string as password");
        assert.strictEqual(list.$('td.o_data_cell:eq(1)').text(), '****',
            "should display string as password");

        list.destroy();
    });

    QUnit.test('list with handle widget', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float" digits="[5,0]"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.strictEqual(args.offset, -4,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2 , 3],
                        "should write the sequence in correct order");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "default first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '500',
            "default second record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '300',
            "default third record should have amount 300");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '0',
            "default fourth record should have amount 0");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "new first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "new second record should have amount 0");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "new third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '300',
            "new fourth record should have amount 300");

        list.destroy();
    });

    QUnit.test('result of consecutive resequences is correctly sorted', async function (assert) {
        assert.expect(9);
        this.data = { // we want the data to be minimal to have a minimal test
            foo: {
                fields: {int_field: {string: "int_field", type: "integer", sortable: true}},
                records: [
                    {id: 1, int_field: 11},
                    {id: 2, int_field: 12},
                    {id: 3, int_field: 13},
                    {id: 4, int_field: 14},
                ]
            }
        };
        var moves = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="id"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    if (moves === 0) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [4, 3],
                            offset: 13,
                            field: "int_field",
                        });
                    }
                    if (moves === 1) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [4, 2],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    if (moves === 2) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [2, 4],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    if (moves === 3) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [4, 2],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    moves += 1;
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(list.$('tbody tr td.o_list_number').text(), '1234',
            "default should be sorted by id");
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').eq(2),
            {position: 'top'}
        );
        assert.strictEqual(list.$('tbody tr td.o_list_number').text(), '1243',
            "the int_field (sequence) should have been correctly updated");

        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1423',
            "the int_field (sequence) should have been correctly updated");

        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(1),
            list.$('tbody tr').eq(3),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1243',
            "the int_field (sequence) should have been correctly updated");

        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1423',
            "the int_field (sequence) should have been correctly updated");
        list.destroy();
    });

    QUnit.test('editable list with handle widget', async function (assert) {
        assert.expect(12);

        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" default_order="int_field">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float" digits="[5,0]"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.strictEqual(args.offset, 1,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2, 3],
                        "should write the sequence in correct order");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "default first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '500',
            "default second record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '300',
            "default third record should have amount 300");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '0',
            "default fourth record should have amount 0");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "new first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "new second record should have amount 0");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "new third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '300',
            "new fourth record should have amount 300");

        await testUtils.dom.click(list.$('tbody tr:eq(1) td:last'));

        assert.strictEqual(list.$('tbody tr:eq(1) td:last input').val(), '0',
            "the edited record should be the good one");

        list.destroy();
    });

    QUnit.test('editable list, handle widget locks and unlocks on sort', async function (assert) {
        assert.expect(6);

        // we need another sortable field to lock/unlock the handle
        this.data.foo.fields.amount.sortable = true;
        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" default_order="int_field">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float"/>' +
                  '</tree>',
        });

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.00500.00300.000.00',
            "default should be sorted by int_field");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // Handle should be unlocked at this point
        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.000.00500.00300.00',
            "drag and drop should have succeeded, as the handle is unlocked");

        // Sorting by a field different for int_field should lock the handle
        await testUtils.dom.click(list.$('.o_column_sortable').eq(1));

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '0.00300.00500.001200.00',
            "should have been sorted by amount");

        // Drag and drop the fourth line in second position (not)
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '0.00300.00500.001200.00',
            "drag and drop should have failed as the handle is locked");

        // Sorting by int_field should unlock the handle
        await testUtils.dom.click(list.$('.o_column_sortable').eq(0));

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.000.00500.00300.00',
            "records should be ordered as per the previous resequence");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.00300.000.00500.00',
            "drag and drop should have worked as the handle is unlocked");

        list.destroy();
    });

    QUnit.test('editable list with handle widget with slow network', async function (assert) {
        assert.expect(15);

        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var prom = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float" digits="[5,0]"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    var _super = this._super.bind(this);
                    assert.strictEqual(args.offset, 1,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2, 3],
                        "should write the sequence in correct order");
                    return prom.then(function () {
                        return _super(route, args);
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "default first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '500',
            "default second record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '300',
            "default third record should have amount 300");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '0',
            "default fourth record should have amount 0");

        // drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // edit moved row before the end of resequence
        await testUtils.dom.click(list.$('tbody tr:eq(3) td:last'));
        await testUtils.nextTick();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 0,
            "shouldn't edit the line before resequence");

        prom.resolve();
        await testUtils.nextTick();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 1,
            "should edit the line after resequence");

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '300',
            "fourth record should have amount 300");

        await testUtils.fields.editInput(list.$('tbody tr:eq(3) td:last input'), 301);
        await testUtils.dom.click(list.$('tbody tr:eq(0) td:last'));

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "second record should have amount 1");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '301',
            "fourth record should have amount 301");

        await testUtils.dom.click(list.$('tbody tr:eq(3) td:last'));
        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '301',
            "fourth record should have amount 301");

        list.destroy();
    });

    QUnit.test('list with handle widget, create, move and discard', async function (assert) {
        // When there are less than 4 records in the table, empty lines are added
        // to have at least 4 rows. This test ensures that the empty line added
        // when a new record is discarded is correctly added on the bottom of
        // the list, even if the discarded record wasn't.
        assert.expect(11);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree editable="bottom">
                    <field name="int_field" widget="handle"/>
                    <field name="foo" required="1"/>
                </tree>`,
            domain: [['bar', '=', false]],
        });

        assert.containsOnce(list, '.o_data_row');
        assert.containsN(list, 'tbody tr', 4);

        await testUtils.dom.click(list.$('.o_list_button_add'));
        assert.containsN(list, '.o_data_row', 2);
        assert.doesNotHaveClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Drag and drop the first line after creating record row
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(0),
            list.$('tbody tr.o_data_row').eq(1),
            { position: 'bottom' }
        );
        assert.containsN(list, '.o_data_row', 2);
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        await testUtils.dom.click(list.$('.o_list_button_discard'));
        assert.containsOnce(list, '.o_data_row');
        assert.hasClass(list.$('tbody tr:first'), 'o_data_row');
        assert.containsN(list, 'tbody tr', 4);

        list.destroy();
    });

    QUnit.test('multiple clicks on Add do not create invalid rows', async function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            m2o: function () {},
        };

        var prom = testUtils.makeTestPromise();
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="m2o" required="1"/></tree>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return prom.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        assert.containsN(list, '.o_data_row', 4,
            "should contain 4 records");

        // click on Add twice, and delay the onchange
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, '.o_data_row', 5,
            "only one record should have been created");

        list.destroy();
    });

    QUnit.test('reference field rendering', async function (assert) {
        assert.expect(4);

        this.data.foo.records.push({
            id: 5,
            reference: 'res_currency,2',
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="reference"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    assert.step(args.model);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['bar', 'res_currency'], "should have done 1 name_get by model in reference values");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').text(), "Value 1USDEUREUR",
            "should have the display_name of the reference");
        list.destroy();
    });

    QUnit.test('reference field batched in grouped list', async function (assert) {
        assert.expect(7);

        this.data.foo.records= [
            // group 1
            {id: 1, foo: '1', reference: 'bar,1'},
            {id: 2, foo: '1', reference: 'bar,2'},
            {id: 3, foo: '1', reference: 'res_currency,1'},
            //group 2
            {id: 4, foo: '2', reference: 'bar,2'},
            {id: 5, foo: '2', reference: 'bar,3'},
        ];
        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `<tree expand="1">
                       <field name="foo" invisible="1"/>
                       <field name="reference"/>
                   </tree>`,
            groupBy: ['foo'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'name_get') {
                    if (args.model === 'bar') {
                        assert.deepEqual(args.args[0], [1, 2 ,3]);
                    }
                    if (args.model === "res.currency") {
                        assert.deepEqual(args.args[0], [1]);
                    }
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.verifySteps([
            'web_read_group',
            'name_get',
            'name_get',
        ]);
        assert.containsN(list, '.o_group_header', 2);
        const allNames = Array.from(list.el.querySelectorAll('.o_data_cell'), node => node.textContent);
        assert.deepEqual(allNames, [
            'Value 1',
            'Value 2',
            'USD',
            'Value 2',
            'Value 3',
        ]);
        list.destroy();
    });

    QUnit.test('editable list view: contexts are correctly sent', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                var context;
                if (route === '/web/dataset/search_read') {
                    context = args.context;
                } else {
                    context = args.kwargs.context;
                }
                assert.strictEqual(context.active_field, 2, "context should be correct");
                assert.strictEqual(context.someKey, 'some value', "context should be correct");
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: {someKey: 'some value'},
            },
            viewOptions: {
                context: {active_field: 2},
            },
        });

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'abc');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        list.destroy();
    });

    QUnit.test('editable list view: contexts with multiple edit', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/foo/write' ||
                    route === '/web/dataset/call_kw/foo/read') {
                    var context = args.kwargs.context;
                    assert.strictEqual(context.active_field, 2, "context should be correct");
                    assert.strictEqual(context.someKey, 'some value', "context should be correct");
                }
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: {someKey: 'some value'},
            },
            viewOptions: {
                context: {active_field: 2},
            },
        });

        // Uses the main selector to select all lines.
        await testUtils.dom.click(list.$('.o_content input:first'));
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        // Edits first record then confirms changes.
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'legion');
        await testUtils.dom.click($('.modal-dialog button.btn-primary'));

        list.destroy();
    });

    QUnit.test('editable list view: single edition with selected records', async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: `<tree editable="top" multi_edit="1"><field name="foo"/></tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        // Select first record
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));

        // Edit the second
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell:first()'));
        await testUtils.fields.editInput(list.$('.o_data_row:eq(1) .o_data_cell:first() input'), "oui");
        await testUtils.dom.click($('.o_list_button_save'));

        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell:first()').text(), "yop",
            "First row should remain unchanged");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell:first()').text(), "oui",
            "Second row should have been updated");

        list.destroy();
    });

    QUnit.test('editable list view: multi edition', async function (assert) {
        assert.expect(26);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" multi_edit="1">' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], { int_field: 666 }],
                        "should write on multi records");
                } else if (args.method === 'read') {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(args.args, [[1, 2], ['foo', 'int_field']],
                            "should batch the read");
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['/web/dataset/search_read']);

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        // edit a line witout modifying a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        assert.hasClass(list.$('.o_data_row:eq(0)'), 'o_selected_row',
            "the first row should be selected");
        await testUtils.dom.click('body');
        assert.containsNone(list, '.o_selected_row', "no row should be selected");

        // create a record and edit its value
        await testUtils.dom.click($('.o_list_button_add'));
        assert.verifySteps(['onchange']);

        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget[name=int_field]'), 123);
        assert.containsNone(document.body, '.modal', "the multi edition should not be triggered during creation");

        await testUtils.dom.click($('.o_list_button_save'));
        assert.verifySteps(['create', 'read']);

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        assert.containsOnce(document.body, '.modal', "modal appears when switching cells");
        await testUtils.dom.click($('.modal .btn:contains(Cancel)'));
        assert.containsN(list, '.o_list_record_selector input:checked', 2,
            "Selection should remain unchanged");
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), 'yop10',
            "changes have been discarded and row is back to readonly");
        assert.strictEqual(document.activeElement, list.$('.o_data_row:eq(0) .o_data_cell:eq(1)')[0],
            "focus should be given to the most recently edited cell after discard");
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell:eq(0)'));
        assert.ok($('.modal').text().includes('those 2 records'), "the number of records should be correctly displayed");
        await testUtils.dom.click($('.modal .btn-primary'));
        assert.containsNone(list, '.o_data_cell input.o_field_widget', "no field should be editable anymore");
        assert.containsNone(list, '.o_list_record_selector input:checked', "no record should be selected anymore");
        assert.verifySteps(['write', 'read']);
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "yop666",
            "the first row should be updated");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "blip666",
            "the second row should be updated");
        assert.containsNone(list, '.o_data_cell input.o_field_widget', "no field should be editable anymore");
        assert.strictEqual(document.activeElement, list.$('.o_data_row:eq(0) .o_data_cell:eq(1)')[0],
            "focus should be given to the most recently edited cell after confirm");

        list.destroy();
    });

    QUnit.test('create in multi editable list', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                    '</tree>',
            intercepts: {
                switch_view: function (ev) {
                    assert.strictEqual(ev.data.view_type, 'form');
                },
            },
        });

        // click on CREATE (should trigger a switch_view)
        await testUtils.dom.click($('.o_list_button_add'));

        list.destroy();
    });

    QUnit.test('editable list view: multi edition cannot call onchanges', async function (assert) {
        assert.expect(15);

        this.data.foo.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length;
            },
        };
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'write') {
                    args.args[1].int_field = args.args[1].foo.length;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['/web/dataset/search_read']);

        // select and edit a single record
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'hi');

        assert.containsNone(document.body, '.modal');
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "hi2");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "blip9");

        assert.verifySteps(['write', 'read']);

        // select the second record (the first one is still selected)
        assert.containsNone(list, '.o_list_record_selector input:checked');
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        // edit foo, first row
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'hello');
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));

        assert.containsOnce(document.body, '.modal'); // save dialog
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "hello5");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "hello5");

        assert.verifySteps(['write', 'read'], "should not perform the onchange in multi edition");

        list.destroy();
    });

    QUnit.test('editable list view: multi edition error and cancellation handling', async function (assert) {
        assert.expect(12);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo" required="1"/>' +
                        '<field name="int_field"/>' +
                    '</tree>',
        });

        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        // edit a line and cancel
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        assert.containsNone(list, '.o_list_record_selector input:enabled');
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget[name=foo]'), "abc");
        await testUtils.dom.click($('.modal .btn:contains("Cancel")'));
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), 'yop10', "first cell should have discarded any change");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        // edit a line with an invalid format type
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        assert.containsNone(list, '.o_list_record_selector input:enabled');
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget[name=int_field]'), "hahaha");
        assert.containsOnce(document.body, '.modal', "there should be an opened modal");
        await testUtils.dom.click($('.modal .btn-primary'));
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), 'yop10', "changes should be discarded");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        // edit a line with an invalid value
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        assert.containsNone(list, '.o_list_record_selector input:enabled');
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget[name=foo]'), "");
        assert.containsOnce(document.body, '.modal', "there should be an opened modal");
        await testUtils.dom.click($('.modal .btn-primary'));
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), 'yop10', "changes should be discarded");
        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        list.destroy();
    });

    QUnit.test('multi edition: many2many_tags in many2many field', async function (assert) {
        assert.expect(5);

        for (let i = 4; i <= 10; i++) {
            this.data.bar.records.push({ id: i, display_name: "Value" + i});
        }

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1"><field name="m2m" widget="many2many_tags"/></tree>',
            archs: {
                'bar,false,list': '<tree><field name="name"/></tree>',
                'bar,false,search': '<search></search>',
            },
        });

        assert.containsN(list, '.o_list_record_selector input:enabled', 5);

        // select two records and enter edit mode
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell'));

        await testUtils.fields.many2one.clickOpenDropdown("m2m");
        await testUtils.fields.many2one.clickItem("m2m", "Search More");
        assert.containsOnce(document.body, '.modal .o_list_view', "should have open the modal");

        await testUtils.dom.click($('.modal .o_list_view .o_data_row:first'));

        assert.containsOnce(document.body, ".modal [role='alert']", "should have open the confirmation modal");
        assert.containsN(document.body, ".modal .o_field_many2manytags .badge", 3);
        assert.strictEqual($(".modal .o_field_many2manytags .badge:last").text().trim(), "Value 3",
            "should have display_name in badge");

        list.destroy();
    });

    QUnit.test('editable list view: multi edition of many2one: set same value', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo"/>' +
                        '<field name="m2o"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2, 3, 4], { m2o: 1 }],
                        "should force write value on all selected records");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('.o_list_many2one').text(), "Value 1Value 2Value 1Value 1");

        // select all records (the first one has value 1 for m2o)
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        // set m2o to 1 in first record
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.many2one.searchAndClickItem('m2o', {search: 'Value 1'});

        assert.containsOnce(document.body, '.modal');

        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        assert.strictEqual(list.$('.o_list_many2one').text(), "Value 1Value 1Value 1Value 1");

        list.destroy();
    });

    QUnit.test('editable list view: clicking on "Discard changes" in multi edition', async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="foo"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        await testUtils.dom.click(list.$('.o_data_row:first() .o_data_cell:first()'));
        list.$('.o_data_row:first() .o_data_cell:first() input').val("oof");

        const $discardButton = list.$buttons.find('.o_list_button_discard');

        // Simulates an actual click (event chain is: mousedown > change > blur > focus > mouseup > click)
        await testUtils.dom.triggerEvents($discardButton, ['mousedown']);
        await testUtils.dom.triggerEvents(list.$('.o_data_row:first() .o_data_cell:first() input'),
            ['change', 'blur', 'focusout']);
        await testUtils.dom.triggerEvents($discardButton, ['focus']);
        $discardButton[0].dispatchEvent(new MouseEvent('mouseup'));
        await testUtils.dom.click($discardButton);

        assert.ok($('.modal').text().includes("Warning"), "Modal should ask to discard changes");
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual(list.$('.o_data_row:first() .o_data_cell:first()').text(), "yop");

        list.destroy();
    });

    QUnit.test('editable list view (multi edition): mousedown on "Discard", but mouseup somewhere else', async function (assert) {
        assert.expect(1);

        const list = await createView({
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        await testUtils.dom.click(list.$('.o_data_row:first() .o_data_cell:first()'));
        list.$('.o_data_row:first() .o_data_cell:first() input').val("oof");

        // Simulates a pseudo drag and drop
        await testUtils.dom.triggerEvents(list.$buttons.find('.o_list_button_discard'), ['mousedown']);
        await testUtils.dom.triggerEvents(list.$('.o_data_row:first() .o_data_cell:first() input'),
            ['change', 'blur', 'focusout']);
        await testUtils.dom.triggerEvents($(document.body), ['focus']);
        window.dispatchEvent(new MouseEvent('mouseup'));
        await testUtils.nextTick();

        assert.ok($('.modal').text().includes("Confirmation"), "Modal should ask to save changes");
        await testUtils.dom.click($('.modal .btn-primary'));

        list.destroy();
    });

    QUnit.test('editable list view: multi edition with readonly modifiers', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="id"/>' +
                        '<field name="foo"/>' +
                        '<field name="int_field" attrs=\'{"readonly": [("id", ">" , 2)]}\'/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], { int_field: 666 }],
                        "should only write on the valid records");
                }
                return this._super.apply(this, arguments);
            },
        });

        // select all records
        await testUtils.dom.click(list.$('th.o_list_record_selector input'));

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);

        const modalText = $('.modal-body').text()
            .split(" ").filter(w => w.trim() !== '').join(" ")
            .split("\n").join('');
        assert.strictEqual(modalText,
            "Among the 4 selected records, 2 are valid for this update. Are you sure you want to " +
            "perform the following update on those 2 records ? Field: int_field Update to: 666");
        assert.strictEqual(document.querySelector('.modal .o_modal_changes .o_field_widget').style.pointerEvents, 'none',
            "pointer events should be deactivated on the demo widget");

        await testUtils.dom.click($('.modal .btn-primary'));
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "1yop666",
            "the first row should be updated");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "2blip666",
            "the second row should be updated");
        list.destroy();
    });

    QUnit.test('editable list view: multi edition when the domain is selected', async function (assert) {
        assert.expect(1);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree multi_edit="1" limit="2">
                    <field name="id"/>
                    <field name="int_field"/>
                </tree>`,
        });

        // select all records, and then select all domain
        await testUtils.dom.click(list.$('th.o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);

        assert.ok($('.modal-body').text().includes('This update will only consider the records of the current page.'));

        list.destroy();
    });

    QUnit.test('editable list view: many2one with readonly modifier', async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch:
                `<tree editable="top">
                    <field name="m2o" readonly="1"/>
                    <field name="foo"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));

        assert.containsOnce(list, '.o_data_row:eq(0) .o_data_cell:eq(0) a[name="m2o"]');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:eq(0) .o_data_cell:eq(1) input')[0],
            "focus should go to the char input");

        list.destroy();
    });

    QUnit.test('editable list view: multi edition server error handling', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo" required="1"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    return Promise.reject();
                }
                return this._super.apply(this, arguments);
            },
        });

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        // edit a line and confirm
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget[name=foo]'), "abc");
        await testUtils.dom.click('body');
        await testUtils.dom.click($('.modal .btn-primary'));
        // Server error: if there was a crash manager, there would be an open error at this point...
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), 'yop',
            "first cell should have discarded any change");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), 'blip',
            "second selected record should not have changed");
        assert.containsNone(list, '.o_data_cell input.o_field_widget',
            "no field should be editable anymore");

        list.destroy();
    });

    QUnit.test('editable readonly list view: navigation', async function (assert) {
        assert.expect(6);

        const list = await createView({
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            data: this.data,
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.res_id, 3,
                        "'switch_view' event has been triggered");
                },
            },
            model: 'foo',
            View: ListView,
        });

        // select 2 records
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(3) .o_list_record_selector input'));

        // toggle a row mode
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell:eq(1)'));
        assert.hasClass(list.$('.o_data_row:eq(1)'), 'o_selected_row',
            "the second row should be selected");

        // Keyboard navigation only interracts with selected elements
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input.o_field_widget[name="int_field"]'), 'enter');
        assert.hasClass(list.$('.o_data_row:eq(3)'), 'o_selected_row',
            "the fourth row should be selected");

        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        assert.hasClass(list.$('.o_data_row:eq(1)'), 'o_selected_row',
            "the second row should be selected again");

        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        assert.hasClass(list.$('.o_data_row:eq(3)'), 'o_selected_row',
            "the fourth row should be selected again");

        await testUtils.dom.click(list.$('.o_data_row:eq(2) .o_data_cell:eq(0)'));
        assert.containsNone(list, '.o_data_cell input.o_field_widget',
            "no row should be editable anymore");
        // Clicking on an unselected record while no row is being edited will open the record (switch_view)
        await testUtils.dom.click(list.$('.o_data_row:eq(2) .o_data_cell:eq(0)'));

        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(3) .o_list_record_selector input'));

        list.destroy();
    });

    QUnit.test('editable list view: multi edition: edit and validate last row', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree multi_edit="1">' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                    '</tree>',
            // in this test, we want to accurately mock what really happens, that is, input
            // fields only trigger their changes on 'change' event, not on 'input'
            fieldDebounce: 100000,
        });

        assert.containsN(list, '.o_data_row', 4);

        // select all records
        await testUtils.dom.click(list.$('.o_list_view thead .o_list_record_selector input'));

        // edit last cell of last line
        await testUtils.dom.click(list.$('.o_data_row:last .o_data_cell:last'));
        testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), '666');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_data_cell:last input'), 'enter');

        assert.containsOnce(document.body, '.modal');
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.containsN(list, '.o_data_row', 4,
            "should not create a new row as we were in multi edition");

        list.destroy();
    });

    QUnit.test('editable readonly list view: navigation in grouped list', async function (assert) {
        assert.expect(6);

        const list = await createView({
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                </tree>`,
            data: this.data,
            groupBy: ['bar'],
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.res_id, 3,
                        "'switch_view' event has been triggered");
                },
            },
            model: 'foo',
            View: ListView,
        });

        // Open both groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_group_header:last'));

        // select 2 records
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(3) .o_list_record_selector input'));

        // toggle a row mode
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell:eq(0)'));
        assert.hasClass(list.$('.o_data_row:eq(1)'), 'o_selected_row',
            "the second row should be selected");

        // Keyboard navigation only interracts with selected elements
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input.o_field_widget'), 'enter');
        assert.hasClass(list.$('.o_data_row:eq(3)'), 'o_selected_row',
            "the fourth row should be selected");

        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        assert.hasClass(list.$('.o_data_row:eq(1)'), 'o_selected_row',
            "the second row should be selected again");

        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        assert.hasClass(list.$('.o_data_row:eq(3)'), 'o_selected_row',
            "the fourth row should be selected again");

        await testUtils.dom.click(list.$('.o_data_row:eq(2) .o_data_cell:eq(0)'));
        assert.containsNone(list, '.o_data_cell input.o_field_widget', "no row should be editable anymore");
        await testUtils.dom.click(list.$('.o_data_row:eq(2) .o_data_cell:eq(0)'));

        list.destroy();
    });

    QUnit.test('editable readonly list view: single edition does not behave like a multi-edition', async function (assert) {
        assert.expect(3);

        const list = await createView({
            arch: `
                <tree multi_edit="1">
                    <field name="foo" required="1"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        // select a record
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));

        // edit a field (invalid input)
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), "");

        assert.containsOnce($('body'),'.modal', "should have a modal (invalid fields)");
        await testUtils.dom.click($('.modal button.btn'));

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), "bar");

        assert.containsNone($('body'),'.modal', "should not have a modal");
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "bar",
            "the first row should be updated");

        list.destroy();
    });

    QUnit.test('editable readonly list view: multi edition', async function (assert) {
        assert.expect(14);

        const list = await createView({
            arch:
                `<tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], { int_field: 666 }],
                        "should write on multi records");
                } else if (args.method === 'read') {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(args.args, [[1, 2], ['foo', 'int_field']],
                            "should batch the read");
                    }
                }
                return this._super.apply(this, arguments);
            },
            model: 'foo',
            View: ListView,
        });

        assert.verifySteps(['/web/dataset/search_read']);

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));

        assert.containsOnce(document.body, '.modal',
            "modal appears when switching cells");

        await testUtils.dom.click($('.modal .btn:contains(Cancel)'));

        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), 'yop10',
            "changes have been discarded and row is back to readonly");

        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell:eq(0)'));

        assert.containsOnce(document.body, '.modal',
            "there should be an opened modal");
        assert.ok($('.modal').text().includes('those 2 records'),
            "the number of records should be correctly displayed");

        await testUtils.dom.click($('.modal .btn-primary'));

        assert.verifySteps(['write', 'read']);
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "yop666",
            "the first row should be updated");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "blip666",
            "the second row should be updated");
        assert.containsNone(list, '.o_data_cell input.o_field_widget',
            "no field should be editable anymore");

        list.destroy();
    });

    QUnit.test('editable list view: m2m tags in grouped list', async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="bar"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            data: this.data,
            groupBy: ['bar'],
            model: 'foo',
            View: ListView,
        });

        // Opens first group
        await testUtils.dom.click(list.$('.o_group_header:first'));

        assert.notEqual(list.$('.o_data_row:first').text(), list.$('.o_data_row:last').text(),
            "First row and last row should have different values");

        await testUtils.dom.click(list.$('thead .o_list_record_selector:first input'));
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:eq(1)'));
        await testUtils.dom.click(list.$('.o_selected_row .o_field_many2manytags .o_delete:first'));
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual(list.$('.o_data_row:first').text(), list.$('.o_data_row:last').text(),
            "All rows should have been correctly updated");

        list.destroy();
    });

    QUnit.test('editable list: edit many2one from external link', async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="m2o"/>
                </tree>`,
            archs: {
                'bar,false,form': '<form string="Bar"><field name="display_name"/></form>',
            },
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
            model: 'foo',
            View: ListView,
        });

        await testUtils.dom.click(list.$('thead .o_list_record_selector:first input'));
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:eq(0)'));
        await testUtils.dom.click(list.$('.o_external_button:first'));

        // Change the M2O value in the Form dialog
        await testUtils.fields.editInput($('.modal input:first'), "OOF");
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual($('.modal .o_field_widget[name=m2o]').text(), "OOF",
            "Value of the m2o should be updated in the confirmation dialog");

        // Close the confirmation dialog
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual(list.$('.o_data_cell:first').text(), "OOF",
            "Value of the m2o should be updated in the list");

        list.destroy();
    });

    QUnit.test('editable list with fields with readonly modifier', async function (assert) {
        assert.expect(8);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree editable="top">
                    <field name="bar"/>
                    <field name="foo" attrs="{'readonly': [['bar','=',True]]}"/>
                    <field name="m2o" attrs="{'readonly': [['bar','=',False]]}"/>
                    <field name="int_field"/>
                </tree>`,
        });

        await testUtils.dom.click(list.$('.o_list_button_add'));

        assert.containsOnce(list, '.o_selected_row');
        assert.notOk(list.$('.o_selected_row .o_field_boolean input').is(':checked'));
        assert.doesNotHaveClass(list.$('.o_selected_row .o_list_char'), 'o_readonly_modifier');
        assert.hasClass(list.$('.o_selected_row .o_list_many2one'), 'o_readonly_modifier');

        await testUtils.dom.click(list.$('.o_selected_row .o_field_boolean input'));

        assert.ok(list.$('.o_selected_row .o_field_boolean input').is(':checked'));
        assert.hasClass(list.$('.o_selected_row .o_list_char'), 'o_readonly_modifier');
        assert.doesNotHaveClass(list.$('.o_selected_row .o_list_many2one'), 'o_readonly_modifier');

        await testUtils.dom.click(list.$('.o_selected_row .o_field_many2one input'));

        assert.strictEqual(document.activeElement, list.$('.o_selected_row .o_field_many2one input')[0]);

        list.destroy();
    });

    QUnit.test('list grouped by date:month', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="date"/></tree>',
            groupBy: ['date:month'],
        });

        assert.strictEqual(list.$('tbody').text(), "January 2017 (1)Undefined (3)",
            "the group names should be correct");

        list.destroy();
    });

    QUnit.test('grouped list edition with toggle_button widget', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="bar" widget="toggle_button"/></tree>',
            groupBy: ['m2o'],
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {bar: false},
                        "should write the correct value");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsOnce(list, '.o_data_row:first .o_toggle_button_success',
            "boolean value of the first record should be true");
        await testUtils.dom.click(list.$('.o_data_row:first .o_icon_button'));
        assert.strictEqual(list.$('.o_data_row:first .text-muted:not(.o_toggle_button_success)').length, 1,
            "boolean button should have been updated");

        list.destroy();
    });

    QUnit.test('grouped list view, indentation for empty group', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/></tree>',
            groupBy: ['priority', 'm2o'],
            mockRPC: function (route, args) {
                // Override of the read_group to display the row even if there is no record in it,
                // to mock the behavihour of some fields e.g stage_id on the sale order.
                if (args.method === 'web_read_group' && args.kwargs.groupby[0] === "m2o") {
                    return Promise.resolve({
                        groups: [{
                            id: 8,
                            m2o: [1, "Value 1"],
                            m2o_count: 0
                        }, {
                            id: 2,
                            m2o: [2, "Value 2"],
                            m2o_count: 1
                        }],
                        length: 1,
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // open the first group
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().length, 1,
            "There should be an empty element creating the indentation for the subgroup.");
        assert.hasClass(list.$('th.o_group_name').eq(1).children().eq(0), 'fa',
            "The first element of the row name should have the fa class");
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().eq(0).is('span'), true,
            "The first element of the row name should be a span");
        list.destroy();
    });

    QUnit.test('basic support for widgets', async function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
            },
            start: function () {
                this.$el.text(JSON.stringify(this.data));
            },
        });
        widgetRegistry.add('test', MyWidget);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/><widget name="test"/></tree>',
        });

        assert.strictEqual(list.$('.o_widget').first().text(), '{"foo":"yop","int_field":10,"id":1}',
            "widget should have been instantiated");

        list.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('use the limit attribute in arch', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.limit, 2,
                    'should use the correct limit value');
                return this._super.apply(this, arguments);
            },
        });


        assert.strictEqual(cpHelpers.getPagerValue(list), '1-2');
        assert.strictEqual(cpHelpers.getPagerSize(list), '4');

        assert.containsN(list, '.o_data_row', 2,
            'should display 2 data rows');
        list.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', async function (assert) {
        assert.expect(2);

        var instanceNumber = 0;
        testUtils.mock.patch(mixins.ParentedMixin, {
            init: function () {
                instanceNumber++;
                return this._super.apply(this, arguments);
            },
            destroy: function () {
                if (!this.isDestroyed()) {
                    instanceNumber--;
                }
                return this._super.apply(this, arguments);
            }
        });

        var params = {
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="date"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="m2o"/>' +
                    '<field name="o2m"/>' +
                    '<field name="m2m"/>' +
                    '<field name="amount"/>' +
                    '<field name="currency_id"/>' +
                    '<field name="datetime"/>' +
                    '<field name="reference"/>' +
                '</tree>',
        };

        var list = await createView(params);
        assert.ok(instanceNumber > 0);

        list.destroy();
        assert.strictEqual(instanceNumber, 0);

        testUtils.mock.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('concurrent reloads finishing in inverse order', async function (assert) {
        assert.expect(4);

        var blockSearchRead = false;
        var prom = testUtils.makeTestPromise();
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read' && blockSearchRead) {
                    return prom.then(_.constant(result));
                }
                return result;
            },
        });

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should contain 4 records");

        // reload with a domain (this request is blocked)
        blockSearchRead = true;
        list.reload({domain: [['foo', '=', 'yop']]});
        await testUtils.nextTick();

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records (search_read being blocked)");

        // reload without the domain
        blockSearchRead = false;
        list.reload({domain: []});
        await testUtils.nextTick();

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records");

        // unblock the RPC
        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records");

        list.destroy();
    });

    QUnit.test('list view on a "noCache" model', async function (assert) {
        assert.expect(9);

        testUtils.mock.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(['foo']),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="display_name"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (_.contains(['create', 'unlink', 'write'], args.method)) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                hasActionMenus: true,
            },
        });
        core.bus.on('clear_cache', list, assert.step.bind(assert, 'clear_cache'));

        // create a new record
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget'), 'some value');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // edit an existing record
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget'), 'new value');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // delete a record
        await testUtils.dom.click(list.$('.o_data_row:first .o_list_record_selector input'));
        await cpHelpers.toggleActionMenu(list);
        await cpHelpers.toggleMenuItem(list, "Delete");
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        assert.verifySteps([
            'create',
            'clear_cache',
            'write',
            'clear_cache',
            'unlink',
            'clear_cache',
        ]);

        list.destroy();
        testUtils.mock.unpatch(BasicModel);

        assert.verifySteps(['clear_cache']); // triggered by the test environment on destroy
    });

    QUnit.test('list should ask to scroll to top on page changes', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="3">' +
                    '<field name="display_name"/>' +
                '</tree>',
            intercepts: {
                scrollTo: function (ev) {
                    assert.strictEqual(ev.data.top, 0,
                        "should ask to scroll to top");
                    assert.step('scroll');
                },
            },
        });


        // switch pages (should ask to scroll)
        await cpHelpers.pagerNext(list);
        await cpHelpers.pagerPrevious(list);
        assert.verifySteps(['scroll', 'scroll'],
            "should ask to scroll when switching pages");

        // change the limit (should not ask to scroll)
        await cpHelpers.setPagerValue(list, '1-2');
        await testUtils.nextTick();
        assert.strictEqual(cpHelpers.getPagerValue(list), '1-2');
        assert.verifySteps([], "should not ask to scroll when changing the limit");

        // switch pages again (should still ask to scroll)
        await cpHelpers.pagerNext(list);

        assert.verifySteps(['scroll'], "this is still working after a limit change");

        list.destroy();
    });

    QUnit.test('list with handle field, override default_get, bottom when inline', async function (assert) {
        assert.expect(2);

        this.data.foo.fields.int_field.default = 10;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom" default_order="int_field">'
                    + '<field name="int_field" widget="handle"/>'
                    + '<field name="foo"/>'
                +'</tree>',
        });

        // starting condition
        assert.strictEqual($('.o_data_cell').text(), "blipblipyopgnap");

        // click add a new line
        // save the record
        // check line is at the correct place

        var inputText = 'ninja';
        await testUtils.dom.click($('.o_list_button_add'));
        await testUtils.fields.editInput(list.$('.o_input[name="foo"]'), inputText);
        await testUtils.dom.click($('.o_list_button_save'));
        await testUtils.dom.click($('.o_list_button_add'));

        assert.strictEqual($('.o_data_cell').text(), "blipblipyopgnap" + inputText);

        list.destroy();
    });

    QUnit.test('create record on list with modifiers depending on id', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="id" invisible="1"/>' +
                    '<field name="foo" attrs="{\'readonly\': [[\'id\',\'!=\',False]]}"/>' +
                    '<field name="int_field" attrs="{\'invisible\': [[\'id\',\'!=\',False]]}"/>' +
                '</tree>',
        });

        // add a new record
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        // modifiers should be evaluted to false
        assert.containsOnce(list, '.o_selected_row');
        assert.doesNotHaveClass(list.$('.o_selected_row .o_data_cell:first'), 'o_readonly_modifier');
        assert.doesNotHaveClass(list.$('.o_selected_row .o_data_cell:nth(1)'), 'o_invisible_modifier');

        // set a value and save
        await testUtils.fields.editInput(list.$('.o_selected_row input[name=foo]'), 'some value');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // modifiers should be evaluted to true
        assert.hasClass(list.$('.o_data_row:first .o_data_cell:first'), 'o_readonly_modifier');
        assert.hasClass(list.$('.o_data_row:first .o_data_cell:nth(1)'), 'o_invisible_modifier');

        // edit again the just created record
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:first'));

        // modifiers should be evaluted to true
        assert.containsOnce(list, '.o_selected_row');
        assert.hasClass(list.$('.o_selected_row .o_data_cell:first'), 'o_readonly_modifier');
        assert.hasClass(list.$('.o_selected_row .o_data_cell:nth(1)'), 'o_invisible_modifier');

        list.destroy();
    });

    QUnit.test('readonly boolean in editable list is readonly', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                      '<field name="foo"/>' +
                      '<field name="bar" attrs="{\'readonly\': [(\'foo\', \'!=\', \'yop\')]}"/>' +
                  '</tree>',
        });

        // clicking on disabled checkbox with active row does not work
        var $disabledCell = list.$('.o_data_row:eq(1) .o_data_cell:last-child');
        await testUtils.dom.click($disabledCell.prev());
        assert.containsOnce($disabledCell, ':disabled:checked');
        var $disabledLabel = $disabledCell.find('.custom-control-label');
        await testUtils.dom.click($disabledLabel);
        assert.containsOnce($disabledCell, ':checked',
            "clicking disabled checkbox did not work"
        );
        assert.ok(
            $(document.activeElement).is('input[type="text"]'),
            "disabled checkbox is not focused after click"
        );

        // clicking on enabled checkbox with active row toggles check mark
        var $enabledCell = list.$('.o_data_row:eq(0) .o_data_cell:last-child');
        await testUtils.dom.click($enabledCell.prev());
        assert.containsOnce($enabledCell, ':checked:not(:disabled)');
        var $enabledLabel = $enabledCell.find('.custom-control-label');
        await testUtils.dom.click($enabledLabel);
        assert.containsNone($enabledCell, ':checked',
            "clicking enabled checkbox worked and unchecked it"
        );
        assert.ok(
            $(document.activeElement).is('input[type="checkbox"]'),
            "enabled checkbox is focused after click"
        );

        list.destroy();
    });

    QUnit.test('grouped list with async widget', async function (assert) {
        assert.expect(4);

        var prom = testUtils.makeTestPromise();
        var AsyncWidget = Widget.extend({
            willStart: function () {
                return prom;
            },
            start: function () {
                this.$el.text('ready');
            },
        });
        widgetRegistry.add('asyncWidget', AsyncWidget);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><widget name="asyncWidget"/></tree>',
            groupBy: ['int_field'],
        });

        assert.containsNone(list, '.o_data_row', "no group should be open");

        await testUtils.dom.click(list.$('.o_group_header:first'));

        assert.containsNone(list, '.o_data_row',
            "should wait for async widgets before opening the group");

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, '.o_data_row', 1, "group should be open");
        assert.strictEqual(list.$('.o_data_row .o_data_cell').text(), 'ready',
            "async widget should be correctly displayed");

        list.destroy();
        delete widgetRegistry.map.asyncWidget;
    });

    QUnit.test('grouped lists with groups_limit attribute', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            groupBy: ['int_field'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(list, '.o_group_header', 3); // page 1
        assert.containsNone(list, '.o_data_row');
        assert.containsOnce(list, '.o_pager'); // has a pager

        await cpHelpers.pagerNext(list); // switch to page 2

        assert.containsN(list, '.o_group_header', 1); // page 2
        assert.containsNone(list, '.o_data_row');

        assert.verifySteps([
            'web_read_group', // read_group page 1
            'web_read_group', // read_group page 2
        ]);

        list.destroy();
    });

    QUnit.test('grouped list with expand attribute', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            }
        });

        assert.containsN(list, '.o_group_header', 2);
        assert.containsN(list, '.o_data_row', 4);
        assert.strictEqual(list.$('.o_data_cell').text(), 'yopblipgnapblip');

        assert.verifySteps([
            'web_read_group', // records are fetched alongside groups
        ]);

        list.destroy();
    });

    QUnit.test('grouped list (two levels) with expand attribute', async function (assert) {
        // the expand attribute only opens the first level groups
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ['bar', 'int_field'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            }
        });

        assert.containsN(list, '.o_group_header', 6);

        assert.verifySteps([
            'web_read_group', // global
            'web_read_group', // first group
            'web_read_group', // second group
        ]);

        list.destroy();
    });

    QUnit.test('grouped lists with expand attribute and a lot of groups', async function (assert) {
        assert.expect(8);

        for (var i = 0; i < 15; i++) {
            this.data.foo.records.push({foo: 'record ' + i, int_field: i});
        }

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ['int_field'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(list, '.o_group_header', 10); // page 1
        assert.containsN(list, '.o_data_row', 11); // one group contains two records
        assert.containsOnce(list, '.o_pager'); // has a pager

        await cpHelpers.pagerNext(list); // switch to page 2

        assert.containsN(list, '.o_group_header', 7); // page 2
        assert.containsN(list, '.o_data_row', 7);

        assert.verifySteps([
            'web_read_group', // read_group page 1
            'web_read_group', // read_group page 2
        ]);

        list.destroy();
    });

    QUnit.test('add filter in a grouped list with a pager', async function (assert) {
        assert.expect(11);

        const actionManager = await createActionManager({
            data: this.data,
            actions: [{
                id: 11,
                name: 'Action 11',
                res_model: 'foo',
                type: 'ir.actions.act_window',
                views: [[3, 'list']],
                search_view_id: [9, 'search'],
                flags: {
                    context: { group_by: ['int_field'] },
                },
            }],
            archs: {
               'foo,3,list': '<tree groups_limit="3"><field name="foo"/></tree>',
               'foo,9,search': `
                    <search>
                        <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                    </search>`,
            },
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(JSON.stringify(args.kwargs.domain) + ', ' + args.kwargs.offset);
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(11);

        assert.containsOnce(actionManager, '.o_list_view');
        assert.strictEqual(actionManager.$('.o_pager_counter').text().trim(), '1-3 / 4');
        assert.containsN(actionManager, '.o_group_header', 3); // page 1

        await testUtils.dom.click(actionManager.$('.o_pager_next')); // switch to page 2

        assert.strictEqual(actionManager.$('.o_pager_counter').text().trim(), '4-4 / 4');
        assert.containsN(actionManager, '.o_group_header', 1); // page 2

        // toggle a filter -> there should be only one group left (on page 1)
        await cpHelpers.toggleFilterMenu(actionManager);
        await cpHelpers.toggleMenuItem(actionManager, 0);

        assert.strictEqual(actionManager.$('.o_pager_counter').text().trim(), '1-1 / 1');
        assert.containsN(actionManager, '.o_group_header', 1); // page 1

        assert.verifySteps([
            '[], undefined',
            '[], 3',
            '[["bar","=",false]], undefined',
        ]);

        actionManager.destroy();
    });

    QUnit.test('editable grouped lists', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group

        // enter edition (grouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        // click on the body should leave the edition
        await testUtils.dom.click($('body'));
        assert.containsNone(list, '.o_selected_row');

        // reload without groupBy
        await list.reload({groupBy: []});

        // enter edition (ungrouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        // click on the body should leave the edition
        await testUtils.dom.click($('body'));
        assert.containsNone(list, '.o_selected_row');

        list.destroy();
    });

    QUnit.test('grouped lists are editable (ungrouped first)', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
        });

        // enter edition (ungrouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        // reload with groupBy
        await list.reload({groupBy: ['bar']});

        // open first group
        await testUtils.dom.click(list.$('.o_group_header:first'));

        // enter edition (grouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        list.destroy();
    });

    QUnit.test('char field edition in editable grouped list', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row .o_data_cell:first input[name="foo"]'), 'pla', 'input');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(this.data.foo.records[0].foo, 'pla',
            "the edition should have been properly saved");
        assert.containsOnce(list, '.o_data_row:first:contains(pla)');

        list.destroy();
    });

    QUnit.test('control panel buttons in editable grouped list views', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        assert.isNotVisible(list.$buttons.find('.o_list_button_add'));

        // reload without groupBy
        await list.reload({groupBy: []});
        assert.isVisible(list.$buttons.find('.o_list_button_add'));

        list.destroy();
    });

    QUnit.test('edit a line and discard it in grouped editable', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:contains(gnap)'));
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third group row should be in edition");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        await testUtils.dom.click(list.$('.o_data_row:nth(0) > td:contains(yop)'));
        assert.ok(list.$('.o_data_row:eq(0)').is('.o_selected_row'),
            "first group row should be in edition");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsNone(list, '.o_selected_row');

        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:contains(gnap)'));
        assert.containsOnce(list, '.o_selected_row');
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third group row should be in edition");

        list.destroy();
    });

    QUnit.test('add and discard a record in a multi-level grouped list view', async function (assert) {
        assert.expect(7);

        testUtils.mock.patch(basicFields.FieldChar, {
            destroy: function () {
                assert.step('destroy');
                this._super.apply(this, arguments);
            },
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ['foo', 'bar'],
        });

        // unfold first subgroup
        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_group_header:eq(1)'));
        assert.hasClass(list.$('.o_group_header:first'), 'o_group_open');
        assert.hasClass(list.$('.o_group_header:eq(1)'), 'o_group_open');
        assert.containsOnce(list, '.o_data_row');

        // add a record to first subgroup
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));
        assert.containsN(list, '.o_data_row', 2);

        // discard
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsOnce(list, '.o_data_row');

        assert.verifySteps(['destroy']);

        testUtils.mock.unpatch(basicFields.FieldChar);
        list.destroy();
    });

    QUnit.test('inputs are disabled when unselecting rows in grouped editable', async function (assert) {
        assert.expect(1);

        var $input;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual($input.prop('disabled'), true,
                        "input should be disabled");
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('td:contains(yop)'));
        $input = list.$('tr.o_selected_row input[name="foo"]');
        await testUtils.fields.editAndTrigger($input, 'lemon', 'input');
        await testUtils.fields.triggerKeydown($input, 'tab');

        list.destroy();
    });

    QUnit.test('pressing ESC in editable grouped list should discard the current line changes', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, 'tr.o_data_row', 3);

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        // update name by "foo"
        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row .o_data_cell:first input[name="foo"]'), 'new_value', 'input');
        // discard by pressing ESC
        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'escape');
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        assert.containsOnce(list, 'tbody tr td:contains(yop)');
        assert.containsN(list, 'tr.o_data_row', 3);
        assert.containsNone(list, 'tr.o_data_row.o_selected_row');
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'));

        list.destroy();
    });

    QUnit.test('pressing TAB in editable="bottom" grouped list', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing TAB in editable="top" grouped list', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing TAB in editable grouped list with create=0', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable="bottom" grouped list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // navigate inside a group
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell')); // select second row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // navigate between groups
        await testUtils.dom.click(list.$('.o_data_cell:eq(3)')); // select row of second group

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable="top" grouped list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // navigate inside a group
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell')); // select second row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // navigate between groups
        await testUtils.dom.click(list.$('.o_data_cell:eq(3)')); // select row of second group

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable grouped list with create="0"', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" create="0"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // navigate inside a group
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell')); // select second row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // navigate between groups
        await testUtils.dom.click(list.$('.o_data_cell:eq(3)')); // select row of second group

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('editing then pressing TAB in editable grouped list', async function (assert) {
        assert.expect(19);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // select and edit last row of first group
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        await testUtils.fields.editInput(list.$('.o_selected_row input[name="foo"]'), 'new value');

        // Press 'Tab' -> should create a new record as we edited the previous one
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.containsN(list, '.o_data_row', 5);
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // fill foo field for the new record and press 'tab' -> should create another record
        await testUtils.fields.editInput(list.$('.o_selected_row input[name="foo"]'), 'new record');
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');

        assert.containsN(list, '.o_data_row', 6);
        assert.hasClass(list.$('.o_data_row:nth(4)'), 'o_selected_row');

        // leave this new row empty and press tab -> should discard the new record and move to the
        // next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row .o_input'), 'tab');
        assert.containsN(list, '.o_data_row', 5);
        assert.hasClass(list.$('.o_data_row:nth(4)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'write',
            'read',
            'onchange',
            'create',
            'read',
            'onchange',
        ]);

        list.destroy();
    });

    QUnit.test('editing then pressing TAB (with a readonly field) in grouped list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
            fieldDebounce: 1
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)'));
        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row input[name="foo"]'), 'new value', 'input');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.containsOnce(list, 'tbody tr td:contains(new value)');
        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            'write',
            'read',
        ]);

        list.destroy();
    });

    QUnit.test('pressing ENTER in editable="bottom" grouped list view', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_group_header:nth(1)')); // open second group
        assert.containsN(list, 'tr.o_data_row', 4);
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell')); // click on second line
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter on last row should create a new record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_input'), 'enter');

        assert.containsN(list, 'tr.o_data_row', 5);
        assert.hasClass(list.$('tr.o_data_row:eq(3)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'onchange',
        ]);

        list.destroy();
    });

    QUnit.test('pressing ENTER in editable="top" grouped list view', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_group_header:nth(1)')); // open second group
        assert.containsN(list, 'tr.o_data_row', 4);
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell')); // click on second line
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter on last row should move to first record of next group
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(3)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
        ]);

        list.destroy();
    });

    QUnit.test('pressing ENTER in editable grouped list view with create=0', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_group_header:nth(1)')); // open second group
        assert.containsN(list, 'tr.o_data_row', 4);
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell')); // click on second line
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter on last row should move to first record of next group
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row .o_input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(3)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
        ]);

        list.destroy();
    });

    QUnit.test('cell-level keyboard navigation in non-editable list', async function (assert) {
        assert.expect(16);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" required="1"/></tree>',
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.res_id, 3,
                        "'switch_view' event has been triggered");
                },
            },
        });

        assert.ok(document.activeElement.classList.contains('o_searchview_input'),
            'default focus should be in search view');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be on the record selector');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.ok(document.activeElement.classList.contains('o_searchview_input'),
            'focus should have come back to the search view');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be in first row input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus should now be in field TD');
        assert.strictEqual(document.activeElement.textContent, 'yop',
            'focus should now be in first row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.textContent, 'yop',
            'should not cycle at end of line');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should now be in second row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'gnap',
            'focus should now be in third row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should now be in last row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should still be in last row field (arrows do not cycle)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should still be in last row field (arrows still do not cycle)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be in last row input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'should not cycle at start of line');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.textContent, 'gnap',
            'focus should now be in third row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        list.destroy();
    });

    QUnit.test('cell-level keyboard navigation in editable grouped list', async function (assert) {
        assert.expect(56);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('td:contains(blip)')); // select row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be opened');

        var $secondRowInput = list.$('tr.o_data_row:eq(1) td:eq(1) input');
        assert.strictEqual($secondRowInput.val(), 'blip',
            'second record should be in edit mode');

        await testUtils.fields.editAndTrigger($secondRowInput, 'blipbloup', 'input');
        assert.strictEqual($secondRowInput.val(), 'blipbloup',
            'second record should be changed but not saved yet');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');

        assert.hasClass($('body'), 'modal-open',
            'record has been modified, are you sure modal should be opened');
        await testUtils.dom.click($('body .modal button span:contains(Ok)'));

        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be closed');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in field td');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of second record should be focused');
        assert.strictEqual(list.$('tr.o_data_row:eq(1) td:eq(1)').text(), 'blip',
            'change should not have been saved');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'record selector should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in first record td');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        var $firstRowInput = list.$('tr.o_data_row:eq(0) td:eq(1) input');
        assert.hasClass(list.$('tr.o_data_row:eq(0)'), 'o_selected_row',
            'first row should be selected');
        assert.strictEqual($firstRowInput.val(), 'yop',
            'first record should be in edit mode');

        await testUtils.fields.editAndTrigger($firstRowInput, 'Zipadeedoodah', 'input');
        assert.strictEqual($firstRowInput.val(), 'Zipadeedoodah',
            'first record should be changed but not saved yet');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row:eq(0) td:eq(1)').text(), 'Zipadeedoodah',
            'first record should be saved');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(0)'), 'o_selected_row',
            'first row should be closed');
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be opened');
        assert.strictEqual(list.$('tr.o_data_row:eq(1) td:eq(1) input').val(), 'blip',
            'second record should be in edit mode');

        assert.strictEqual(document.activeElement.value, 'blip',
            'second record input should be focused');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.value, 'blip',
            'second record input should still be focused (arrows movements are disabled in edit)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.value, 'blip',
            'second record input should still be focused (arrows movements are still disabled in edit)');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be closed');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in field td');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of second record should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');

        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');

        assert.strictEqual(document.activeElement.textContent, 'false (1)',
            'focus should be on second group header');
        assert.strictEqual(list.$('tr.o_data_row').length, 3,
            'should have 3 rows displayed');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row').length, 4,
            'should have 4 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'false (1)',
            'focus should still be on second group header');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of last record should be focused');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'arrow navigation should not cycle (focus still on last row)');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        await testUtils.fields.editAndTrigger($('tr.o_data_row:eq(4) td:eq(1) input'),
            'cheateur arrete de cheater', 'input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row').length, 6,
            'should have 6 rows displayed (new record + new edit line)');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');

        // come back to the top
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');

        assert.strictEqual(document.activeElement.tagName, 'TH',
            'focus is in table header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus is in header input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in field td');
        assert.strictEqual(document.activeElement.textContent, 'Zipadeedoodah',
            'second field of first record should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus should be on first group header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed (first group should be closed)');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus should still be on first group header');

        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(list.$('tr.o_data_row').length, 5,
            'should have 5 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(list.$('tr.o_data_row').length, 5,
            'should have 5 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'false (2)',
            'focus should now be on second group header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'record td should be focused');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of first record of second group should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'cheateur arrete de cheater',
            'second field of last record of second group should be focused');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.strictEqual(document.activeElement.textContent, 'cheateur arrete de cheater',
        'second field of last record of second group should be focused (special case: the first td of the "Add a line" line was skipped');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of first record of second group should be focused');

        list.destroy();
    });

    QUnit.test('execute group header button with keyboard navigation', async function (assert) {
        assert.expect(13);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<groupby name="m2o">' +
                        '<button type="object" name="some_method" string="Do this"/>' +
                    '</groupby>' +
                '</tree>',
            groupBy: ['m2o'],
            intercepts: {
                execute_action: function (ev) {
                    assert.strictEqual(ev.data.action_data.name, 'some_method');
                },
            },
        });

        assert.containsNone(list, '.o_data_row', "all groups should be closed");

        // focus create button as a starting point
        list.$('.o_list_button_add').focus();
        assert.ok(document.activeElement.classList.contains('o_list_button_add'));
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be on the record selector (list header)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'Value 1 (3)',
            'focus should be on first group header');

        // unfold first group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.containsN(list, '.o_data_row', 3, "first group should be open");

        // move to first record of opened group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should be in first row checkbox');

        // move back to the group header
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.ok(document.activeElement.classList.contains('o_group_name'),
            'focus should be back on first group header');

        // fold the group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.ok(document.activeElement.classList.contains('o_group_name'),
            'focus should still be on first group header');
        assert.containsNone(list, '.o_data_row', "first group should now be folded");

        // unfold the group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.ok(document.activeElement.classList.contains('o_group_name'),
            'focus should still be on first group header');
        assert.containsN(list, '.o_data_row', 3, "first group should be open");

        // simulate a move to the group header button with tab (we can't trigger a native event
        // programmatically, see https://stackoverflow.com/a/32429197)
        list.$('.o_group_header .o_group_buttons button:first').focus();
        assert.strictEqual(document.activeElement.tagName, 'BUTTON',
            'focus should be on the group header button');

        // click on the button by pressing enter
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.containsN(list, '.o_data_row', 3, "first group should still be open");

        list.destroy();
    });

    QUnit.test('add a new row in grouped editable="top" list', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));// add a new row
        assert.strictEqual(list.$('.o_selected_row .o_input[name=foo]')[0], document.activeElement,
            'The first input of the line should have the focus');
        assert.containsN(list, 'tbody:nth(1) .o_data_row', 4);

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard')); // discard new row
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsOnce(list, 'tbody:nth(3) .o_data_row');

        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        assert.strictEqual(list.$('.o_group_name:eq(1)').text(), 'false (2)',
            "group should have correct name and count");
        assert.containsN(list, 'tbody:nth(3) .o_data_row', 2);
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row input[name="foo"]'), 'pla', 'input');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsN(list, 'tbody:nth(3) .o_data_row', 2);

        list.destroy();
    });

    QUnit.test('add a new row in grouped editable="bottom" list', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));// add a new row
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');
        assert.containsN(list, 'tbody:nth(1) .o_data_row', 4);

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard')); // discard new row
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsOnce(list, 'tbody:nth(3) .o_data_row');
        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        assert.hasClass(list.$('.o_data_row:nth(4)'), 'o_selected_row');

        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row input[name="foo"]'), 'pla', 'input');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsN(list, 'tbody:nth(3) .o_data_row', 2);

        list.destroy();
    });

    QUnit.test('add and discard a line through keyboard navigation without crashing', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        // Triggers ENTER on "Add a line" wrapper cell
        await testUtils.fields.triggerKeydown(list.$('.o_group_field_row_add'), 'enter');
        assert.containsN(list, 'tbody:nth(1) .o_data_row', 4, "new data row should be created");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        // At this point, a crash manager should appear if no proper link targetting
        assert.containsN(list, 'tbody:nth(1) .o_data_row', 3,"new data row should be discarded.");

        list.destroy();
    });

    QUnit.test('editable grouped list with create="0"', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" create="0"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        assert.containsNone(list, '.o_group_field_row_add a',
            "Add a line should not be available in readonly");

        list.destroy();
    });

    QUnit.test('add a new row in (selection) grouped editable list', async function (assert) {
        assert.expect(6);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                        '<field name="priority"/>' +
                        '<field name="m2o"/>' +
                    '</tree>',
            groupBy: ['priority'],
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.step(args.kwargs.context.default_priority.toString());
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        await testUtils.dom.click(list.$('.o_group_field_row_add a')); // add a new row
        await testUtils.dom.click($('body')); // unselect row
        assert.verifySteps(['1']);
        assert.strictEqual(list.$('.o_data_row .o_data_cell:eq(1)').text(), 'Low',
            "should have a column name with a value from the groupby");

        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        await testUtils.dom.click($('body')); // unselect row
        assert.strictEqual(list.$('.o_data_row:nth(5) .o_data_cell:eq(1)').text(), 'Medium',
            "should have a column name with a value from the groupby");
        assert.verifySteps(['2']);

        list.destroy();
    });

    QUnit.test('add a new row in (m2o) grouped editable list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                        '<field name="m2o"/>' +
                    '</tree>',
            groupBy: ['m2o'],
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.step(args.kwargs.context.default_m2o.toString());
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));
        await testUtils.dom.click($('body')); // unselect row
        assert.strictEqual(list.$('tbody:eq(1) .o_data_row:first .o_data_cell:eq(1)').text(), 'Value 1',
            "should have a column name with a value from the groupby");
        assert.verifySteps(['1']);

        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        await testUtils.dom.click($('body')); // unselect row
        assert.strictEqual(list.$('tbody:eq(3) .o_data_row:first .o_data_cell:eq(1)').text(), 'Value 2',
            "should have a column name with a value from the groupby");
        assert.verifySteps(['2']);

        list.destroy();
    });

    QUnit.test('list view with optional fields rendering', async function (assert) {
        assert.expect(12);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="amount"/>' +
                    '<field name="reference" optional="hide"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
            translateParameters: {
                direction: 'ltr',
            }
        });

        assert.containsN(list, 'th', 3,
            "should have 3 th, 1 for selector, 2 for columns");

        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle',
            "should have the optional columns dropdown toggle inside the table");

        const optionalFieldsToggler = list.el.querySelector('table').lastElementChild.previousSibling;
        assert.ok(optionalFieldsToggler.classList.contains('o_optional_columns_dropdown_toggle'),
            'The optional fields toggler is the second last element');
        const optionalFieldsDropdown = list.el.querySelector('table').lastElementChild;
        assert.ok(optionalFieldsDropdown.classList.contains('o_optional_columns'),
            'The optional fields dropdown is the last element');

        assert.ok(list.$('.o_optional_columns .dropdown-menu').hasClass('dropdown-menu-right'),
            'In LTR, the dropdown should be anchored to the right and expand to the left');

        // optional fields
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.containsN(list, 'div.o_optional_columns div.dropdown-item', 2,
            "dropdown have 2 optional field foo with checked and bar with unchecked");

        // enable optional field
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        // 5 th (1 for checkbox, 4 for columns)
        assert.containsN(list, 'th', 4, "should have 4 th");
        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        // disable optional field
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.strictEqual(list.$('div.o_optional_columns div.dropdown-item:first input:checked')[0],
            list.$('div.o_optional_columns div.dropdown-item [name="m2o"]')[0],
            "m2o advanced field check box should be checked in dropdown");

        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        // 3 th (1 for checkbox, 2 for columns)
        assert.containsN(list, 'th', 3, "should have 3 th");
        assert.notOk(list.$('th:contains(M2O field)').is(':visible'),
            "should not have a visible m2o field"); //m2o field not displayed

        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.notOk(list.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));

        list.destroy();
    });

    QUnit.test('list view with optional fields rendering in RTL mode', async function (assert) {
        assert.expect(4);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="amount"/>' +
                    '<field name="reference" optional="hide"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
            translateParameters: {
                direction: 'rtl',
            }
        });

        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle',
            "should have the optional columns dropdown toggle inside the table");

        const optionalFieldsToggler = list.el.querySelector('table').lastElementChild.previousSibling;
        assert.ok(optionalFieldsToggler.classList.contains('o_optional_columns_dropdown_toggle'),
            'The optional fields toggler is the last element');
        const optionalFieldsDropdown = list.el.querySelector('table').lastElementChild;
        assert.ok(optionalFieldsDropdown.classList.contains('o_optional_columns'),
            'The optional fields is the last element');

        assert.ok(list.$('.o_optional_columns .dropdown-menu').hasClass('dropdown-menu-left'),
            'In RTL, the dropdown should be anchored to the left and expand to the right');

        list.destroy();
    });

    QUnit.test('optional fields do not disappear even after listview reload', async function (assert) {
        assert.expect(7);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="amount"/>' +
                    '<field name="reference" optional="hide"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.containsN(list, 'th', 3,
            "should have 3 th, 1 for selector, 2 for columns");

        // enable optional field
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.notOk(list.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        assert.containsN(list, 'th', 4,
            "should have 4 th 1 for selector, 3 for columns");
        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        // reload listview
        await list.reload();
        assert.containsN(list, 'th', 4,
            "should have 4 th 1 for selector, 3 for columns ever after listview reload");
        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field even after listview reload");

        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.ok(list.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));

        list.destroy();
    });

    QUnit.test('selection is kept when optional fields are toggled', async function (assert) {
        assert.expect(7);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.containsN(list, 'th', 2);

        // select a record
        await testUtils.dom.click(list.$('.o_data_row .o_list_record_selector input:first'));

        assert.containsOnce(list, '.o_list_record_selector input:checked');

        // add an optional field
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        assert.containsN(list, 'th', 3);

        assert.containsOnce(list, '.o_list_record_selector input:checked');

        // select all records
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));

        assert.containsN(list, '.o_list_record_selector input:checked', 5);

        // remove an optional field
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        assert.containsN(list, 'th', 2);

        assert.containsN(list, '.o_list_record_selector input:checked', 5);

        list.destroy();
    });

    QUnit.test('list view with optional fields and async rendering', async function (assert) {
        assert.expect(14);

        const prom = testUtils.makeTestPromise();
        const FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            async _render() {
                assert.ok(true, 'the rendering must be async');
                this._super(...arguments);
                await prom;
            },
        }));

        const RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="m2o"/>
                    <field name="foo" widget="asyncwidget" optional="hide"/>
                </tree>`,
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.containsN(list, 'th', 2);
        assert.isNotVisible(list.$('.o_optional_columns_dropdown'));

        // add an optional field (we click on the label on purpose, as it will trigger
        // a second event on the input)
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.isVisible(list.$('.o_optional_columns_dropdown'));
        assert.containsNone(list.$('.o_optional_columns_dropdown'), 'input:checked');
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first label'));

        assert.containsN(list, 'th', 2);
        assert.isVisible(list.$('.o_optional_columns_dropdown'));
        assert.containsNone(list.$('.o_optional_columns_dropdown'), 'input:checked');

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, 'th', 3);
        assert.isVisible(list.$('.o_optional_columns_dropdown'));
        assert.containsOnce(list.$('.o_optional_columns_dropdown'), 'input:checked');

        list.destroy();
        delete fieldRegistry.map.asyncwidget;
    });

    QUnit.test('change the viewType of the current action', async function (assert) {
        assert.expect(25);

        this.actions = [{
            id: 1,
            name: 'Partners Action 1',
            res_model: 'foo',
            type: 'ir.actions.act_window',
            views: [[1, 'kanban']],
        }, {
            id: 2,
            name: 'Partners',
            res_model: 'foo',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [1, 'kanban']],
        }];

        this.archs = {
            'foo,1,kanban': '<kanban><templates><t t-name="kanban-box">' +
            '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
            '</t></templates></kanban>',

            'foo,false,list': '<tree limit="3">' +
            '<field name="foo"/>' +
            '<field name="m2o" optional="hide"/>' +
            '<field name="o2m" optional="show"/></tree>',

            'foo,false,search': '<search><field name="foo" string="Foo"/></search>',
        };

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var actionManager = await testUtils.createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
        });
        await actionManager.doAction(2);

        assert.containsOnce(actionManager, '.o_list_view',
            "should have rendered a list view");

        assert.containsN(actionManager, 'th', 3, "should display 3 th (selector + 2 fields)");

        // enable optional field
        await testUtils.dom.click(actionManager.$('table .o_optional_columns_dropdown_toggle'));
        assert.notOk(actionManager.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));
        assert.ok(actionManager.$('div.o_optional_columns div.dropdown-item [name="o2m"]').is(":checked"));
        await testUtils.dom.click(actionManager.$('div.o_optional_columns div.dropdown-item:first'));
        assert.containsN(actionManager, 'th', 4, "should display 4 th (selector + 3 fields)");
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        // switch to kanban view
        await actionManager.loadState({
            action: 2,
            view_type: 'kanban',
        });

        assert.containsNone(actionManager, '.o_list_view',
            "should not display the list view anymore");
        assert.containsOnce(actionManager, '.o_kanban_view',
            "should have switched to the kanban view");

        // switch back to list view
        await actionManager.loadState({
            action: 2,
            view_type: 'list',
        });

        assert.containsNone(actionManager, '.o_kanban_view',
            "should not display the kanban view anymoe");
        assert.containsOnce(actionManager, '.o_list_view',
            "should display the list view");

        assert.containsN(actionManager, 'th', 4, "should display 4 th");
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field
        assert.ok(actionManager.$('th:contains(O2M field)').is(':visible'),
            "should have a visible o2m field"); //m2o field

        // disable optional field
        await testUtils.dom.click(actionManager.$('table .o_optional_columns_dropdown_toggle'));
        assert.ok(actionManager.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));
        assert.ok(actionManager.$('div.o_optional_columns div.dropdown-item [name="o2m"]').is(":checked"));
        await testUtils.dom.click(actionManager.$('div.o_optional_columns div.dropdown-item:last input'));
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field
        assert.notOk(actionManager.$('th:contains(O2M field)').is(':visible'),
            "should have a visible o2m field"); //m2o field
        assert.containsN(actionManager, 'th', 3, "should display 3 th");

        await actionManager.doAction(1);

        assert.containsNone(actionManager, '.o_list_view',
            "should not display the list view anymore");
        assert.containsOnce(actionManager, '.o_kanban_view',
            "should have switched to the kanban view");

        await actionManager.doAction(2);

        assert.containsNone(actionManager, '.o_kanban_view',
            "should not havethe kanban view anymoe");
        assert.containsOnce(actionManager, '.o_list_view',
            "should display the list view");

        assert.containsN(actionManager, 'th', 3, "should display 3 th");
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field
        assert.notOk(actionManager.$('th:contains(O2M field)').is(':visible'),
            "should have a visible o2m field"); //m2o field

        actionManager.destroy();
    });

    QUnit.test('list view with optional fields rendering and local storage mock', async function (assert) {
        assert.expect(12);

        var forceLocalStorage = true;

        var Storage = RamStorage.extend({
            getItem: function (key) {
                assert.step('getItem ' + key);
                return forceLocalStorage ? '["m2o"]' : this._super.apply(this, arguments);
            },
            setItem: function (key, value) {
                assert.step('setItem ' + key + ' to ' + value);
                return this._super.apply(this, arguments);
            },
        });

        var RamStorageService = AbstractStorageService.extend({
            storage: new Storage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<field name="m2o" optional="hide"/>' +
                '<field name="reference" optional="show"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
            view_id: 42,
        });

        var localStorageKey = 'optional_fields,foo,list,42,foo,m2o,reference';

        assert.verifySteps(['getItem ' + localStorageKey]);

        assert.containsN(list, 'th', 3,
            "should have 3 th, 1 for selector, 2 for columns");

        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        assert.notOk(list.$('th:contains(Reference Field)').is(':visible'),
            "should not have a visible reference field");

        // optional fields
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.containsN(list, 'div.o_optional_columns div.dropdown-item', 2,
            "dropdown have 2 optional fields");

        forceLocalStorage = false;
        // enable optional field
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:eq(1) input'));

        assert.verifySteps([
            'setItem ' + localStorageKey + ' to ["m2o","reference"]',
            'getItem ' + localStorageKey,
        ]);

        // 4 th (1 for checkbox, 3 for columns)
        assert.containsN(list, 'th', 4, "should have 4 th");

        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        assert.ok(list.$('th:contains(Reference Field)').is(':visible'),
            "should have a visible reference field");

        list.destroy();
    });
    QUnit.test("quickcreate in a many2one in a list", async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: '<tree editable="top"><field name="m2o"/></tree>',
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:first'));

        const $input = list.$('.o_data_row:first .o_data_cell:first input');
        await testUtils.fields.editInput($input, "aaa");
        $input.trigger('keyup');
        $input.trigger('blur');
        document.body.click();

        await testUtils.nextTick();

        assert.containsOnce(document.body, '.modal', "the quick_create modal should appear");

        await testUtils.dom.click($('.modal .btn-primary:first'));
        await testUtils.dom.click(document.body);

        assert.strictEqual(list.el.getElementsByClassName('o_data_cell')[0].innerHTML, "aaa",
            "value should have been updated");

        list.destroy();
    });

    QUnit.test('float field render with digits attribute on listview', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="qux" digits="[12,6]"/></tree>',
        });

        assert.strictEqual(list.$('td.o_list_number:eq(0)').text(), "0.400000", "should contain 6 digits decimal precision");
        list.destroy();
    });
    // TODO: write test on:
    // - default_get with a field not in view

    QUnit.test('editable list: resize column headers', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="reference" optional="hide"/>' +
                '</tree>',
        });

        // Target handle
        const th = list.el.getElementsByTagName('th')[1];
        const optionalDropdown = list.el.getElementsByClassName('o_optional_columns')[0];
        const optionalInitialX = optionalDropdown.getBoundingClientRect().x;
        const resizeHandle = th.getElementsByClassName('o_resize')[0];
        const originalWidth = th.offsetWidth;
        const expectedWidth = Math.floor(originalWidth / 2 + resizeHandle.offsetWidth / 2);
        const delta = originalWidth - expectedWidth;

        await testUtils.dom.dragAndDrop(resizeHandle, th, { mousemoveTarget: window, mouseupTarget: window });
        const optionalFinalX = Math.floor(optionalDropdown.getBoundingClientRect().x);

        assert.strictEqual(th.offsetWidth, expectedWidth,
            // 1px for the cell right border
            "header width should be halved (plus half the width of the handle)");
        assert.strictEqual(optionalFinalX, optionalInitialX - delta,
            "optional columns dropdown should have moved the same amount");

        list.destroy();
    });

    QUnit.test('resize column with several x2many lists in form group', async function (assert) {
        assert.expect(3);

        this.data.bar.fields.text = {string: "Text field", type: "char"};
        this.data.foo.records[0].o2m = [1, 2];

        const form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: `
                <form>
                    <group>
                        <field name="o2m">
                            <tree editable="bottom">
                                <field name="display_name"/>
                                <field name="text"/>
                            </tree>
                        </field>
                        <field name="m2m">
                            <tree editable="bottom">
                                <field name="display_name"/>
                                <field name="text"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            res_id: 1,
        });

        const th = form.el.getElementsByTagName('th')[0];
        const resizeHandle = th.getElementsByClassName('o_resize')[0];
        const firstTableInitialWidth = form.el.querySelectorAll('.o_field_x2many_list table')[0].offsetWidth;
        const secondTableInititalWidth = form.el.querySelectorAll('.o_field_x2many_list table')[1].offsetWidth;

        assert.strictEqual(firstTableInitialWidth, secondTableInititalWidth,
            "both table columns have same width");

        await testUtils.dom.dragAndDrop(resizeHandle, form.el.getElementsByTagName('th')[1], { position: "right" });

        assert.notEqual(firstTableInitialWidth, form.el.querySelectorAll('thead')[0].offsetWidth,
            "first o2m table is resized and width of table has changed");
        assert.strictEqual(secondTableInititalWidth, form.el.querySelectorAll('thead')[1].offsetWidth,
            "second o2m table should not be impacted on first o2m in group resized");

        form.destroy();
    });

    QUnit.test('enter edition in editable list with <widget>', async function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            start: function () {
                this.$el.html('<i class="fa fa-info"/>');
            },
        });
        widgetRegistry.add('some_widget', MyWidget);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<widget name="some_widget"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                '</tree>',
        });

        // click on int_field cell of first row
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:nth(1)'));
        assert.strictEqual(document.activeElement.name, "int_field");

        list.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('enter edition in editable list with multi_edit = 0', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" multi_edit="0">' +
                '<field name="int_field"/>' +
                '</tree>',
        });

        // click on int_field cell of first row
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:nth(0)'));
        assert.strictEqual(document.activeElement.name, "int_field");

        list.destroy();
    });

    QUnit.test('enter edition in editable list with multi_edit = 1', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" multi_edit="1">' +
                '<field name="int_field"/>' +
                '</tree>',
        });

        // click on int_field cell of first row
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:nth(0)'));
        assert.strictEqual(document.activeElement.name, "int_field");

        list.destroy();
    });

    QUnit.test('list view with field component: mounted and willUnmount calls', async function (assert) {
        // this test could be removed as soon as the list view will be written in Owl
        assert.expect(7);

        let mountedCalls = 0;
        let willUnmountCalls = 0;
        class MyField extends AbstractFieldOwl {
            mounted() {
                mountedCalls++;
            }
            willUnmount() {
                willUnmountCalls++;
            }
        }
        MyField.template = owl.tags.xml`<span>Hello World</span>`;
        fieldRegistryOwl.add('my_owl_field', MyField);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" widget="my_owl_field"/></tree>',
        });

        assert.containsN(list, '.o_data_row', 4);
        assert.strictEqual(mountedCalls, 4);
        assert.strictEqual(willUnmountCalls, 0);

        await list.reload();
        assert.strictEqual(mountedCalls, 8);
        assert.strictEqual(willUnmountCalls, 4);

        list.destroy();
        assert.strictEqual(mountedCalls, 8);
        assert.strictEqual(willUnmountCalls, 8);
    });

    QUnit.test('editable list view: multi edition of owl field component', async function (assert) {
        // this test could be removed as soon as all field widgets will be written in owl
        assert.expect(5);

        const list = await createView({
            arch: '<tree multi_edit="1"><field name="bar"/></tree>',
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        assert.containsN(list, '.o_data_row', 4);
        assert.containsN(list, '.o_data_cell .custom-checkbox input:checked', 3);

        // select all records and edit the boolean field
        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsN(list, '.o_data_row .o_list_record_selector input:checked', 4);
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.dom.click(list.$('.o_data_cell .o_field_boolean input'));

        assert.containsOnce(document.body, '.modal');
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        assert.containsNone(list, '.o_data_cell .custom-checkbox input:checked');

        list.destroy();
    });

    QUnit.test("Date in evaluation context works with date field", async function (assert) {
        assert.expect(11);

        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        const unpatchDate = testUtils.mock.patchDate(1997, 0, 9, 12, 0, 0);
        testUtils.mock.patch(BasicModel, {
            _getEvalContext() {
                const evalContext = this._super(...arguments);
                assert.ok(dateRegex.test(evalContext.today));
                assert.strictEqual(evalContext.current_date, evalContext.today);
                return evalContext;
            },
        });

        this.data.foo.fields.birthday = { string: "Birthday", type: 'date' };
        this.data.foo.records[0].birthday = "1997-01-08";
        this.data.foo.records[1].birthday = "1997-01-09";
        this.data.foo.records[2].birthday = "1997-01-10";

        const list = await createView({
            arch: `
                <tree>
                    <field name="birthday" decoration-danger="birthday > today"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        assert.containsOnce(list, ".o_data_row .text-danger");

        list.destroy();
        unpatchDate();
        testUtils.mock.unpatch(BasicModel);
    });

    QUnit.test("Datetime in evaluation context works with datetime field", async function (assert) {
        assert.expect(6);

        const datetimeRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
        const unpatchDate = testUtils.mock.patchDate(1997, 0, 9, 12, 0, 0);
        testUtils.mock.patch(BasicModel, {
            _getEvalContext() {
                const evalContext = this._super(...arguments);
                assert.ok(datetimeRegex.test(evalContext.now));
                return evalContext;
            },
        });

        /**
         * Returns "1997-01-DD HH:MM:00" with D, H and M holding current UTC values
         * from patched date + (deltaMinutes) minutes.
         * This is done to allow testing from any timezone since UTC values are
         * calculated with the offset of the current browser.
         */
        function dateStringDelta(deltaMinutes) {
            const d = new Date(Date.now() + 1000 * 60 * deltaMinutes);
            return `1997-01-${
                String(d.getUTCDate()).padStart(2, '0')
            } ${
                String(d.getUTCHours()).padStart(2, '0')
            }:${
                String(d.getUTCMinutes()).padStart(2, '0')
            }:00`;
        }

        // "datetime" field may collide with "datetime" object in context
        this.data.foo.fields.birthday = { string: "Birthday", type: 'datetime' };
        this.data.foo.records[0].birthday = dateStringDelta(-30);
        this.data.foo.records[1].birthday = dateStringDelta(0);
        this.data.foo.records[2].birthday = dateStringDelta(+30);

        const list = await createView({
            arch: `
                <tree>
                    <field name="birthday" decoration-danger="birthday > now"/>
                </tree>`,
            data: this.data,
            model: 'foo',
            View: ListView,
        });

        assert.containsOnce(list, ".o_data_row .text-danger");

        list.destroy();
        unpatchDate();
        testUtils.mock.unpatch(BasicModel);
    });
});

});
