odoo.define('web.view_dialogs_tests', function (require) {
"use strict";

var dialogs = require('web.view_dialogs');
var ListController = require('web.ListController');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var FormView = require('web.FormView');

const { browser } = require('@web/core/browser/browser');
const { patchWithCleanup } = require('@web/../tests/helpers/utils');
const cpHelpers = require('@web/../tests/search/helpers');
var createView = testUtils.createView;

async function createParent(params) {
    var widget = new Widget();
    params.server = await testUtils.mock.addMockEnvironment(widget, params);
    return widget;
}

QUnit.module('LegacyViews', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: "boolean"},
                    instrument: {string: 'Instruments', type: 'many2one', relation: 'instrument'},
                },
                records: [
                    {id: 1, foo: 'blip', display_name: 'blipblip', bar: true},
                    {id: 2, foo: 'ta tata ta ta', display_name: 'macgyver', bar: false},
                    {id: 3, foo: 'piou piou', display_name: "Jack O'Neill", bar: true},
                ],
            },
            instrument: {
                fields: {
                    name: {string: "name", type: "char"},
                    badassery: {string: 'level', type: 'many2many', relation: 'badassery', domain: [['level', '=', 'Awsome']]},
                },
            },

            badassery: {
                fields: {
                    level: {string: 'level', type: "char"},
                },
                records: [
                    {id: 1, level: 'Awsome'},
                ],
            },

            product: {
                fields : {
                    name: {string: "name", type: "char" },
                    partner : {string: 'Doors', type: 'one2many', relation: 'partner'},
                },
                records: [
                    {id: 1, name: 'The end'},
                ],
            },
        };
    },
}, function () {

    QUnit.module('ViewDialog (legacy)');

    QUnit.test('formviewdialog buttons in footer are positioned properly', async function (assert) {
        assert.expect(2);

        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                        '<sheet>' +
                            '<group><field name="foo"/></group>' +
                            '<footer><button string="Custom Button" type="object" class="btn-primary"/></footer>' +
                        '</sheet>' +
                    '</form>',
            },
        });

        new dialogs.FormViewDialog(parent, {
            res_model: 'partner',
            res_id: 1,
        }).open();
        await testUtils.nextTick();

        assert.notOk($('.modal-body button').length,
            "should not have any button in body");
        assert.strictEqual($('.modal-footer button').length, 1,
            "should have only one button in footer");
        parent.destroy();
    });

    QUnit.test('formviewdialog buttons in footer are not duplicated', async function (assert) {
        assert.expect(2);
        this.data.partner.fields.poney_ids = {string: "Poneys", type: "one2many", relation: 'partner'};
        this.data.partner.records[0].poney_ids = [];

        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                            '<field name="poney_ids"><tree editable="top"><field name="display_name"/></tree></field>' +
                            '<footer><button string="Custom Button" type="object" class="btn-primary"/></footer>' +
                    '</form>',
            },
        });

        new dialogs.FormViewDialog(parent, {
            res_model: 'partner',
            res_id: 1,
        }).open();
        await testUtils.nextTick();

        assert.strictEqual($('.modal button.btn-primary').length, 1,
            "should have 1 buttons in modal");

        await testUtils.dom.click($('.o_field_x2many_list_row_add a'));
        await testUtils.fields.triggerKeydown($('input.o_input'), 'escape');

        assert.strictEqual($('.modal button.btn-primary').length, 1,
            "should still have 1 buttons in modal");
        parent.destroy();
    });

    QUnit.test('SelectCreateDialog use domain, group_by and search default', async function (assert) {
        assert.expect(3);

        var search = 0;
        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree string="Partner">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                        '<field name="foo" filter_domain="[(\'display_name\',\'ilike\',self), (\'foo\',\'ilike\',self)]"/>' +
                        '<group expand="0" string="Group By">' +
                            '<filter name="groupby_bar" context="{\'group_by\' : \'bar\'}"/>' +
                        '</group>' +
                    '</search>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.deepEqual(args.kwargs, {
                        context: {
                            search_default_foo: "piou",
                            search_default_groupby_bar: true,
                        },
                        domain: ["&", ["display_name", "like", "a"], "&", ["display_name", "ilike", "piou"], ["foo", "ilike", "piou"]],
                        fields: ["display_name", "foo", "bar"],
                        groupby: ["bar"],
                        orderby: '',
                        lazy: true,
                        limit: 80,
                    }, "should search with the complete domain (domain + search), and group by 'bar'");
                }
                if (search === 0 && route === '/web/dataset/search_read') {
                    search++;
                    assert.deepEqual(args, {
                        context: {
                            search_default_foo: "piou",
                            search_default_groupby_bar: true,
                            bin_size: true
                        },  // not part of the test, may change
                        domain: ["&", ["display_name", "like", "a"], "&", ["display_name", "ilike", "piou"], ["foo", "ilike", "piou"]],
                        fields: ["display_name", "foo"],
                        model: "partner",
                        limit: 80,
                        sort: ""
                    }, "should search with the complete domain (domain + search)");
                } else if (search === 1 && route === '/web/dataset/search_read') {
                    assert.deepEqual(args, {
                        context: {
                            search_default_foo: "piou",
                            search_default_groupby_bar: true,
                            bin_size: true
                        },  // not part of the test, may change
                        domain: [["display_name", "like", "a"]],
                        fields: ["display_name", "foo"],
                        model: "partner",
                        limit: 80,
                        sort: ""
                    }, "should search with the domain");
                }

                return this._super.apply(this, arguments);
            },
        });

        new dialogs.SelectCreateDialog(parent, {
            no_create: true,
            readonly: true,
            res_model: 'partner',
            domain: [['display_name', 'like', 'a']],
            context: {
                search_default_groupby_bar: true,
                search_default_foo: 'piou',
            },
        }).open();
        await testUtils.nextTick();
        const modal = document.body.querySelector(".modal");
        await cpHelpers.removeFacet(modal, "Bar");
        await cpHelpers.removeFacet(modal);

        parent.destroy();
    });

    QUnit.test('SelectCreateDialog correctly evaluates domains', async function (assert) {
        assert.expect(1);

        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree string="Partner">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                        '<field name="foo"/>' +
                    '</search>',
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [['id', '=', 2]],
                        "should have correctly evaluated the domain");
                }
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: {uid: 2},
            },
        });

        new dialogs.SelectCreateDialog(parent, {
            no_create: true,
            readonly: true,
            res_model: 'partner',
            domain: "[['id', '=', uid]]",
        }).open();
        await testUtils.nextTick();

        parent.destroy();
    });

    QUnit.test('SelectCreateDialog list view in readonly', async function (assert) {
        assert.expect(1);

        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree string="Partner" editable="bottom">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search/>'
            },
        });

        var dialog;
        new dialogs.SelectCreateDialog(parent, {
            res_model: 'partner',
        }).open().then(function (result) {
            dialog = result;
        });
        await testUtils.nextTick();

        // click on the first row to see if the list is editable
        await testUtils.dom.click(dialog.$('.o_legacy_list_view tbody tr:first td:not(.o_list_record_selector):first'));

        assert.equal(dialog.$('.o_legacy_list_view tbody tr:first td:not(.o_list_record_selector):first input').length, 0,
            "list view should not be editable in a SelectCreateDialog");

        parent.destroy();
    });

    QUnit.test('SelectCreateDialog cascade x2many in create mode', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'product',
            data: this.data,
            arch: '<form>' +
                     '<field name="name"/>' +
                     '<field name="partner" widget="one2many" >' +
                        '<tree editable="top">' +
                            '<field name="display_name"/>' +
                            '<field name="instrument"/>' +
                        '</tree>' +
                    '</field>' +
                  '</form>',
            res_id: 1,
            archs: {
                'partner,false,form': '<form>' +
                                           '<field name="name"/>' +
                                           '<field name="instrument" widget="one2many" mode="tree"/>' +
                                        '</form>',

                'instrument,false,form': '<form>'+
                                            '<field name="name"/>'+
                                            '<field name="badassery">' +
                                                '<tree>'+
                                                    '<field name="level"/>'+
                                                '</tree>' +
                                            '</field>' +
                                        '</form>',

                'badassery,false,list': '<tree>'+
                                                '<field name="level"/>'+
                                            '</tree>',

                'badassery,false,search': '<search>'+
                                                '<field name="level"/>'+
                                            '</search>',
            },

            mockRPC: function(route, args) {
                if (route === '/web/dataset/call_kw/partner/get_formview_id') {
                    return Promise.resolve(false);
                }
                if (route === '/web/dataset/call_kw/instrument/get_formview_id') {
                    return Promise.resolve(false);
                }
                if (route === '/web/dataset/call_kw/instrument/create') {
                    assert.deepEqual(args.args, [{badassery: [[6, false, [1]]], name: "ABC"}],
                        'The method create should have been called with the right arguments');
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
        });

        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.many2one.createAndEdit("instrument");

        var $modal = $('.modal-lg');

        assert.equal($modal.length, 1,
            'There should be one modal');

        await testUtils.dom.click($modal.find('.o_field_x2many_list_row_add a'));

        var $modals = $('.modal-lg');

        assert.equal($modals.length, 2,
            'There should be two modals');

        var $second_modal = $modals.not($modal);
        await testUtils.dom.click($second_modal.find('.o_list_table.table.table-sm.table-striped.o_list_table_ungrouped .o_data_row input[type=checkbox]'));

        await testUtils.dom.click($second_modal.find('.o_select_button'));

        $modal = $('.modal-lg');

        assert.equal($modal.length, 1,
            'There should be one modal');

        assert.equal($modal.find('.o_data_cell').text(), 'Awsome',
            'There should be one item in the list of the modal');

        await testUtils.dom.click($modal.find('.btn.btn-primary'));

        form.destroy();
    });

    QUnit.test('Form dialog and subview with _view_ref contexts', async function (assert) {
        assert.expect(2);

        this.data.instrument.records = [{id: 1, name: 'Tromblon', badassery: [1]}];
        this.data.partner.records[0].instrument = 1;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                     '<field name="name"/>' +
                     '<field name="instrument" context="{\'tree_view_ref\': \'some_tree_view\'}"/>' +
                  '</form>',
            res_id: 1,
            archs: {
                'instrument,false,form': '<form>'+
                                            '<field name="name"/>'+
                                            '<field name="badassery" context="{\'tree_view_ref\': \'some_other_tree_view\'}"/>' +
                                        '</form>',

                'badassery,false,list': '<tree>'+
                                                '<field name="level"/>'+
                                            '</tree>',
            },
            viewOptions: {
                mode: 'edit',
            },

            mockRPC: function(route, args) {
                if (args.method === 'get_formview_id') {
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },

            interceptsPropagate: {
                load_views: function (ev) {
                    var evaluatedContext = ev.data.context;
                    if (ev.data.modelName === 'instrument') {
                        assert.deepEqual(evaluatedContext, {tree_view_ref: 'some_tree_view'},
                            'The correct _view_ref should have been sent to the server, first time');
                    }
                    if (ev.data.modelName === 'badassery') {
                        assert.deepEqual(evaluatedContext, {
                            base_model_name: 'instrument',
                            tree_view_ref: 'some_other_tree_view',
                        }, 'The correct _view_ref should have been sent to the server for the subview');
                    }
                },
            },
        });

        await testUtils.dom.click(form.$('.o_field_widget[name="instrument"] button.o_external_button'));
        form.destroy();
    });

    QUnit.test("Form dialog replaces the context with _createContext method when specified", async function (assert) {
        assert.expect(5);

        const parent = await createParent({
            data: this.data,
            archs: {
                "partner,false,form":
                    `<form string="Partner">
                        <sheet>
                            <group><field name="foo"/></group>
                        </sheet>
                    </form>`,
            },

            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.step(JSON.stringify(args.kwargs.context));
                }
                return this._super(route, args);
            },
        });

        new dialogs.FormViewDialog(parent, {
            res_model: "partner",
            context: { answer: 42 },
            _createContext: () => ({ dolphin: 64 }),
        }).open();
        await testUtils.nextTick();

        assert.notOk($(".modal-body button").length,
            "should not have any button in body");
        assert.strictEqual($(".modal-footer button").length, 3,
            "should have 3 buttons in footer");

        await testUtils.dom.click($(".modal-footer button:contains(Save & New)"));
        await testUtils.dom.click($(".modal-footer button:contains(Save & New)"));
        assert.verifySteps(['{"answer":42}', '{"dolphin":64}']);
        parent.destroy();
    });

    QUnit.test("Form dialog keeps full context when no _createContext is specified", async function (assert) {
        assert.expect(5);

        const parent = await createParent({
            data: this.data,
            archs: {
                "partner,false,form":
                    `<form string="Partner">
                        <sheet>
                            <group><field name="foo"/></group>
                        </sheet>
                    </form>`,
            },

            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.step(JSON.stringify(args.kwargs.context));
                }
                return this._super(route, args);
            },
        });

        new dialogs.FormViewDialog(parent, {
            res_model: "partner",
            context: { answer: 42 }
        }).open();
        await testUtils.nextTick();

        assert.notOk($(".modal-body button").length,
            "should not have any button in body");
        assert.strictEqual($(".modal-footer button").length, 3,
            "should have 3 buttons in footer");

        await testUtils.dom.click($(".modal-footer button:contains(Save & New)"));
        await testUtils.dom.click($(".modal-footer button:contains(Save & New)"));
        assert.verifySteps(['{"answer":42}', '{"answer":42}']);
        parent.destroy();
    });

    QUnit.test('SelectCreateDialog: save current search', async function (assert) {
        assert.expect(4);

        testUtils.mock.patch(ListController, {
            getOwnedQueryParams: function () {
                return {
                    context: {
                        shouldBeInFilterContext: true,
                    },
                };
            },
        });

        // save favorite needs this
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree>' +
                        '<field name="display_name"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                       '<filter name="bar" help="Bar" domain="[(\'bar\', \'=\', True)]"/>' +
                    '</search>',

            },
            env: {
                dataManager: {
                    create_filter: function (filter) {
                        assert.strictEqual(filter.domain, `[("bar", "=", True)]`,
                            "should save the correct domain");
                        const expectedContext = {
                            group_by: [], // default groupby is an empty list
                            shouldBeInFilterContext: true,
                        };
                        assert.deepEqual(filter.context, expectedContext,
                            "should save the correct context");
                    },
                }
            },
        });

        var dialog;
        new dialogs.SelectCreateDialog(parent, {
            context: {shouldNotBeInFilterContext: false},
            res_model: 'partner',
        }).open().then(function (result) {
            dialog = result;
        });
        await testUtils.nextTick();


        assert.containsN(dialog, '.o_data_row', 3, "should contain 3 records");

        // filter on bar
        const modal = document.body.querySelector(".modal");
        await cpHelpers.toggleFilterMenu(modal);
        await cpHelpers.toggleMenuItem(modal, "Bar");

        assert.containsN(dialog, '.o_data_row', 2, "should contain 2 records");

        // save filter
        await cpHelpers.toggleFavoriteMenu(modal);
        await cpHelpers.toggleSaveFavorite(modal);
        await cpHelpers.editFavoriteName(modal, "some name");
        await cpHelpers.saveFavorite(modal);

        testUtils.mock.unpatch(ListController);
        parent.destroy();
    });

    QUnit.test('SelectCreateDialog calls on_selected with every record matching the domain', async function (assert) {
        assert.expect(3);

        const parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree limit="2" string="Partner">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                        '<field name="foo"/>' +
                    '</search>',
            },
            session: {},
        });

        new dialogs.SelectCreateDialog(parent, {
            res_model: 'partner',
            on_selected: function(records) {
                assert.equal(records.length, 3);
                assert.strictEqual(records.map((r) => r.display_name).toString(), "blipblip,macgyver,Jack O'Neill");
                assert.strictEqual(records.map((r) => r.id).toString(), "1,2,3");
            }
        }).open();
        await testUtils.nextTick();

        await testUtils.dom.click($('thead .o_list_record_selector input'));
        await testUtils.dom.click($('.o_list_selection_box .o_list_select_domain'));
        await testUtils.dom.click($('.modal .o_select_button'));

        parent.destroy();
    });

    QUnit.test('SelectCreateDialog calls on_selected with every record matching without selecting a domain', async function (assert) {
        assert.expect(3);

        const parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree limit="2" string="Partner">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                        '<field name="foo"/>' +
                    '</search>',
            },
            session: {},
        });

        new dialogs.SelectCreateDialog(parent, {
            res_model: 'partner',
            on_selected: function(records) {
                assert.equal(records.length, 2);
                assert.strictEqual(records.map((r) => r.display_name).toString(), "blipblip,macgyver");
                assert.strictEqual(records.map((r) => r.id).toString(), "1,2");
            }
        }).open();
        await testUtils.nextTick();

        await testUtils.dom.click($('thead .o_list_record_selector input'));
        await testUtils.dom.click($('.o_list_selection_box '));
        await testUtils.dom.click($('.modal .o_select_button'));

        parent.destroy();
    });

    QUnit.test('propagate can_create onto the search popup o2m', async function (assert) {
        assert.expect(4);

        this.data.instrument.records = [
            {id: 1, name: 'Tromblon1'},
            {id: 2, name: 'Tromblon2'},
            {id: 3, name: 'Tromblon3'},
            {id: 4, name: 'Tromblon4'},
            {id: 5, name: 'Tromblon5'},
            {id: 6, name: 'Tromblon6'},
            {id: 7, name: 'Tromblon7'},
            {id: 8, name: 'Tromblon8'},
        ];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                     '<field name="name"/>' +
                     '<field name="instrument" can_create="false"/>' +
                  '</form>',
            res_id: 1,
            archs: {
                'instrument,false,list': '<tree>'+
                                                '<field name="name"/>'+
                                            '</tree>',
                'instrument,false,search': '<search>'+
                                                '<field name="name"/>'+
                                            '</search>',
            },
            viewOptions: {
                mode: 'edit',
            },

            mockRPC: function(route, args) {
                if (args.method === 'get_formview_id') {
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
        });

        await testUtils.fields.many2one.clickOpenDropdown('instrument');

        assert.containsNone(form, '.ui-autocomplete a:contains(Start typing...)');

        await testUtils.fields.editInput(form.el.querySelector(".o_field_many2one[name=instrument] input"), "a");

        assert.containsNone(form, '.ui-autocomplete a:contains(Create and Edit)');

        await testUtils.fields.editInput(form.el.querySelector(".o_field_many2one[name=instrument] input"), "");
        await testUtils.fields.many2one.clickItem('instrument', 'Search More...');

        var $modal = $('.modal-dialog.modal-lg');

        assert.strictEqual($modal.length, 1, 'Modal present');

        assert.strictEqual($modal.find('.modal-footer button').text(), "Cancel",
            'Only the cancel button is present in modal');

        form.destroy();
    });

    QUnit.test('formviewdialog is not closed when button handlers return a rejected promise', async function (assert) {
        assert.expect(3);

        this.data.partner.fields.poney_ids = { string: "Poneys", type: "one2many", relation: 'partner' };
        this.data.partner.records[0].poney_ids = [];
        var reject = true;

        var parent = await createParent({
            data: this.data,
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                    '<field name="poney_ids"><tree><field name="display_name"/></tree></field>' +
                    '</form>',
            },
        });

        new dialogs.FormViewDialog(parent, {
            res_model: 'partner',
            res_id: 1,
            buttons: [{
                text: 'Click me !',
                classes: "btn-secondary o_form_button_magic",
                close: true,
                click: function () {
                    return reject ? Promise.reject() : Promise.resolve();
                },
            }],
        }).open();

        await testUtils.nextTick();
        assert.strictEqual($('.modal').length, 1, "should have a modal displayed");

        await testUtils.dom.click($('.modal .o_form_button_magic'));
        assert.strictEqual($('.modal').length, 1, "modal should still be opened");

        reject = false;
        await testUtils.dom.click($('.modal .o_form_button_magic'));
        assert.strictEqual($('.modal').length, 0, "modal should be closed");

        parent.destroy();
    });

});

});
