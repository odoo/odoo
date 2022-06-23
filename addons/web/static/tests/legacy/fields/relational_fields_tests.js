odoo.define('web.relational_fields_tests', function (require) {
"use strict";

var AbstractStorageService = require('web.AbstractStorageService');
var FormView = require('web.FormView');
const KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var RamStorage = require('web.RamStorage');
var relationalFields = require('web.relational_fields');
var testUtils = require('web.test_utils');
const core = require('web.core');
const makeTestEnvironment = require("web.test_env");
const { makeLegacyCommandService } = require("@web/legacy/utils");
const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
const { getFixture, triggerHotkey, nextTick, click } = require("@web/../tests/helpers/utils");
const { registry } = require("@web/core/registry");

const { makeLegacyDialogMappingTestEnv } = require('@web/../tests/helpers/legacy_env_utils');

const cpHelpers = require('@web/../tests/search/helpers');
var createView = testUtils.createView;

QUnit.module('Legacy fields', {}, function () {

QUnit.module('Legacy relational_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    bar: {string: "Bar", type: "boolean", default: true},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1] },
                    p: {string: "one2many field", type: "one2many", relation: 'partner', relation_field: 'trululu'},
                    turtles: {string: "one2many turtle field", type: "one2many", relation: 'turtle', relation_field: 'turtle_trululu'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    color: {
                        type: "selection",
                        selection: [['red', "Red"], ['black', "Black"]],
                        default: 'red',
                        string: "Color",
                    },
                    date: {string: "Some Date", type: "date"},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                    user_id: {string: "User", type: 'many2one', relation: 'user'},
                    reference: {string: "Reference Field", type: 'reference', selection: [
                        ["product", "Product"], ["partner_type", "Partner Type"], ["partner", "Partner"]]},
                    model_id: {string: "Model", type:'many2one', relation:'ir.model'}
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    bar: true,
                    foo: "yop",
                    int_field: 10,
                    qux: 0.44,
                    p: [],
                    turtles: [2],
                    timmy: [],
                    trululu: 4,
                    user_id: 17,
                    reference: 'product,37',
                }, {
                    id: 2,
                    display_name: "second record",
                    bar: true,
                    foo: "blip",
                    int_field: 9,
                    qux: 13,
                    p: [],
                    timmy: [],
                    trululu: 1,
                    product_id: 37,
                    date: "2017-01-25",
                    datetime: "2016-12-12 10:55:05",
                    user_id: 17,
                }, {
                    id: 4,
                    display_name: "aaa",
                    bar: false,
                }],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"}
                },
                records: [{
                    id: 37,
                    display_name: "xphone",
                }, {
                    id: 41,
                    display_name: "xpad",
                }]
            },
            partner_type: {
                fields: {
                    name: {string: "Partner Type", type: "char"},
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 12, display_name: "gold", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                ]
            },
            turtle: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    turtle_foo: {string: "Foo", type: "char"},
                    turtle_bar: {string: "Bar", type: "boolean", default: true},
                    turtle_int: {string: "int", type: "integer", sortable: true},
                    turtle_description: {string: "Description", type: "text"},
                    turtle_trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    turtle_ref: {string: "Reference", type: 'reference', selection: [
                        ["product", "Product"], ["partner", "Partner"]]},
                    product_id: {string: "Product", type: "many2one", relation: 'product', required: true},
                    partner_ids: {string: "Partner", type: "many2many", relation: 'partner'},
                },
                records: [{
                    id: 1,
                    display_name: "leonardo",
                    turtle_bar: true,
                    turtle_foo: "yop",
                    partner_ids: [],
                }, {
                    id: 2,
                    display_name: "donatello",
                    turtle_bar: true,
                    turtle_foo: "blip",
                    turtle_int: 9,
                    partner_ids: [2,4],
                }, {
                    id: 3,
                    display_name: "raphael",
                    product_id: 37,
                    turtle_bar: false,
                    turtle_foo: "kawa",
                    turtle_int: 21,
                    partner_ids: [],
                    turtle_ref: 'product,37',
                }],
                onchanges: {},
            },
            user: {
                fields: {
                    name: {string: "Name", type: "char"},
                    partner_ids: {string: "one2many partners field", type: "one2many", relation: 'partner', relation_field: 'user_id'},
                },
                records: [{
                    id: 17,
                    name: "Aline",
                    partner_ids: [1, 2],
                }, {
                    id: 19,
                    name: "Christine",
                }]
            },
            'ir.model': {
                fields: {
                    model: {string: "Model", type: "char"},
                },
                records: [{
                    id: 17,
                    name: "Partner",
                    model: 'partner',
                }, {
                    id: 20,
                    name: "Product",
                    model: 'product',
                }, {
                    id: 21,
                    name: "Partner Type",
                    model: 'partner_type',
                }],
                onchanges: {},
            },
        };
    },
}, function () {

    QUnit.test('search more pager is reset when doing a new search', async function (assert) {
        assert.expect(6);

        this.data.partner.records.push(
            ...new Array(170).fill().map((_, i) => ({ id: i + 10, name: "Partner " + i }))
        );
        this.data.partner.fields.datetime.searchable = true;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,list': '<tree><field name="display_name"/></tree>',
                'partner,false,search': '<search><field name="datetime"/><field name="display_name"/></search>',
            },
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        await testUtils.fields.many2one.clickOpenDropdown('trululu');
        await testUtils.fields.many2one.clickItem('trululu','Search');
        await testUtils.dom.click($('.modal .o_pager_next'));

        assert.strictEqual($('.o_pager_limit').text(), "1173", "there should be 173 records");
        assert.strictEqual($('.o_pager_value').text(), "181-160", "should display the second page");
        assert.strictEqual($('tr.o_data_row').length, 80, "should display 80 record");

        const modal = document.body.querySelector(".modal");
        await cpHelpers.editSearch(modal, "first");
        await cpHelpers.validateSearch(modal);

        assert.strictEqual($('.o_pager_limit').text(), "11", "there should be 1 record");
        assert.strictEqual($('.o_pager_value').text(), "11-1", "should display the first page");
        assert.strictEqual($('tr.o_data_row').length, 1, "should display 1 record");
        form.destroy();
    });

    QUnit.test('do not call name_get if display_name already known', async function (assert) {
        assert.expect(4);

        this.data.partner.fields.product_id.default = 37;
        this.data.partner.onchanges = {
            trululu: function (obj) {
                obj.trululu = 1;
            },
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="trululu"/><field name="product_id"/></form>',
            mockRPC: function (route, args) {
                assert.step(args.method + ' on ' + args.model);
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=trululu] input').val(), 'first record');
        assert.strictEqual(form.$('.o_field_widget[name=product_id] input').val(), 'xphone');
        assert.verifySteps(['onchange on partner']);

        form.destroy();
    });

    QUnit.test('x2many default_order multiple fields', async function (assert) {
        assert.expect(7);

        this.data.partner.records = [
            {int_field: 10, id: 1, display_name: "record1"},
            {int_field: 12, id: 2, display_name: "record2"},
            {int_field: 11, id: 3, display_name: "record3"},
            {int_field: 12, id: 4, display_name: "record4"},
            {int_field: 10, id: 5, display_name: "record5"},
            {int_field: 10, id: 6, display_name: "record6"},
            {int_field: 11, id: 7, display_name: "record7"},
        ];

        this.data.partner.records[0].p = [1, 7, 4, 5, 2, 6, 3];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                        '<field name="p" >' +
                            '<tree default_order="int_field,id">' +
                                '<field name="id"/>' +
                                '<field name="int_field"/>' +
                            '</tree>' +
                        '</field>' +
                '</form>',
            res_id: 1,
        });

        var $recordList = form.$('.o_field_x2many_list .o_data_row');
        var expectedOrderId = ['1', '5', '6', '3', '7', '2', '4'];

        _.each($recordList, function(record, index) {
            var $record = $(record);
            assert.strictEqual($record.find('.o_data_cell').eq(0).text(), expectedOrderId[index],
                'The record should be the right place. Index: ' + index);
        });

        form.destroy();
    });

    QUnit.test('focus when closing many2one modal in many2one modal', async function (assert) {
        assert.expect(12);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="trululu"/>' +
                  '</form>',
            res_id: 2,
            archs: {
                'partner,false,form': '<form><field name="trululu"/></form>'
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
        });

        // Open many2one modal
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_external_button'));

        var $originalModal = $('.modal');
        var $focusedModal = $(document.activeElement).closest('.modal');

        assert.equal($originalModal.length, 1, 'There should be one modal');
        assert.equal($originalModal[0], $focusedModal[0], 'Modal is focused');
        assert.ok($('body').hasClass('modal-open'), 'Modal is said opened');

        // Open many2one modal of field in many2one modal
        await testUtils.dom.click($originalModal.find('.o_external_button'));
        var $modals = $('.modal');
        $focusedModal = $(document.activeElement).closest('.modal');

        assert.equal($modals.length, 2, 'There should be two modals');
        assert.equal($modals[1], $focusedModal[0], 'Last modal is focused');
        assert.ok($('body').hasClass('modal-open'), 'Modal is said opened');

        // Close second modal
        await testUtils.dom.click($modals.last().find('button[class="close"]'));
        var $modal = $('.modal');
        $focusedModal = $(document.activeElement).closest('.modal');

        assert.equal($modal.length, 1, 'There should be one modal');
        assert.equal($modal[0], $originalModal[0], 'First modal is still opened');
        assert.equal($modal[0], $focusedModal[0], 'Modal is focused');
        assert.ok($('body').hasClass('modal-open'), 'Modal is said opened');

        // Close first modal
        await testUtils.dom.click($modal.find('button[class="close"]'));
        $modal = $('.modal-dialog.modal-lg');

        assert.equal($modal.length, 0, 'There should be no modal');
        assert.notOk($('body').hasClass('modal-open'), 'Modal is not said opened');

        form.destroy();
    });


    QUnit.test('one2many from a model that has been sorted', async function (assert) {
        assert.expect(1);

        /* On a standard list view, sort your records by a field
         * Click on a record which contains a x2m with multiple records in it
         * The x2m shouldn't take the orderedBy of the parent record (the one on the form)
         */

        this.data.partner.records[0].turtles = [3, 2];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree>' +
                            '<field name="turtle_foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            context: {
                orderedBy: [{
                    name: 'foo',
                    asc: false,
                }]
            },
        });

        assert.strictEqual(form.$('.o_field_one2many[name=turtles] .o_data_row')
            .text().trim(), "kawablip", 'The o2m should not have been sorted.');

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes in a subview', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<notebook>' +
                            '<page string="Turtles">' +
                                '<field name="turtles" mode="tree">' +
                                    '<tree>' +
                                        '<field name="id"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
            '</form>',
            archs: {
                'turtle,false,form': '<form>' +
                    '<field name="partner_ids" widget="many2many_checkboxes"/>' +
                '</form>',
            },
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_data_cell'));
        // edit the partner_ids field by (un)checking boxes on the widget
        var $firstCheckbox = $('.modal .custom-control-input').first();
        await testUtils.dom.click($firstCheckbox);
        assert.ok($firstCheckbox.prop('checked'), "the checkbox should be ticked");
        var $secondCheckbox = $('.modal .custom-control-input').eq(1);
        await testUtils.dom.click($secondCheckbox);
        assert.notOk($secondCheckbox.prop('checked'), "the checkbox should be unticked");
        form.destroy();
    });

    QUnit.test('embedded readonly one2many with handle widget', async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].turtles = [1, 2, 3];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="turtles" readonly="1">' +
                            '<tree editable="top">' +
                                '<field name="turtle_int" widget="handle"/>' +
                                '<field name="turtle_foo"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                 '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_row_handle').length, 3,
            "there should be 3 handles (one for each row)");
        assert.strictEqual(form.$('.o_row_handle:visible').length, 0,
            "the handles should be hidden in readonly mode");

        await testUtils.form.clickEdit(form);

        assert.strictEqual(form.$('.o_row_handle').length, 3,
            "the handles should still be there");
        assert.strictEqual(form.$('.o_row_handle:visible').length, 0,
            "the handles should still be hidden (on readonly fields)");

        form.destroy();
    });

    QUnit.test('prevent the dialog in readonly x2many tree view with option no_open True', async function (assert) {
        assert.expect(2);
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="turtles">' +
                            '<tree editable="bottom" no_open="True">' +
                                '<field name="turtle_foo"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                 '</form>',
            res_id: 1,
        });
        assert.containsOnce(form, '.o_data_row:contains("blip")', "There should be one record in x2many list view")
        await testUtils.dom.click(form.$('.o_data_row:first'));
        assert.strictEqual($('.modal-dialog').length, 0, "There is should be no dialog open on click of readonly list row");
        form.destroy();
    });

    QUnit.test('delete a record while adding another one in a multipage', async function (assert) {
        // in a many2one with at least 2 pages, add a new line. Delete the line above it.
        // (the onchange makes it so that the virtualID is inserted in the middle of the currentResIDs.)
        // it should load the next line to display it on the page.
        assert.expect(2);

        this.data.partner.records[0].turtles = [2, 3];
        this.data.partner.onchanges.turtles = function (obj) {
           obj.turtles = [[5]].concat(obj.turtles);
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="turtles">' +
                                '<tree editable="bottom" limit="1" decoration-muted="turtle_bar == False">' +
                                    '<field name="turtle_foo"/>' +
                                    '<field name="turtle_bar"/>' +
                                '</tree>' +
                            '</field>' +
                        '</group>' +
                    '</sheet>' +
                 '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        // add a line (virtual record)
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.fields.editInput(form.$('.o_input'), 'pi');
        // delete the line above it
        await testUtils.dom.click(form.$('.o_list_record_remove').first());
        await testUtils.owlCompatibilityExtraNextTick();
        // the next line should be displayed below the newly added one
        assert.strictEqual(form.$('.o_data_row').length, 2, "should have 2 records");
        assert.strictEqual(form.$('.o_data_row .o_data_cell:first-child').text(), 'pikawa',
            "should display the correct records on page 1");

        form.destroy();
    });

    QUnit.test('one2many, onchange, edition and multipage...', async function (assert) {
        assert.expect(8);

        this.data.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [[5]].concat(obj.turtles);
            }
        };

        this.data.partner.records[0].turtles = [1,2,3];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree editable="bottom" limit="2">' +
                            '<field name="turtle_foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(args.method + ' ' + args.model);
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), 'nora');
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

        assert.verifySteps([
            'read partner',
            'read turtle',
            'onchange turtle',
            'onchange partner',
            "onchange partner",
            'onchange turtle',
            'onchange partner',
        ]);
        form.destroy();
    });

    QUnit.test('onchange on unloaded record clearing posterious change', async function (assert) {
        // when we got onchange result for fields of record that were not
        // already available because they were in a inline view not already
        // opened, in a given configuration the change were applied ignoring
        // posteriously changed data, thus an added/removed/modified line could
        // be reset to the original onchange data
        assert.expect(5);

        var numUserOnchange = 0;

        this.data.user.onchanges = {
            partner_ids: function (obj) {
                // simulate actual server onchange after save of modal with new record
                if (numUserOnchange === 0) {
                    obj.partner_ids = _.clone(obj.partner_ids);
                    obj.partner_ids.unshift([5]);
                    obj.partner_ids[1][2].turtles.unshift([5]);
                    obj.partner_ids[2] = [1, 2, {
                        display_name: 'second record',
                        trululu: 1,
                        turtles: [[5]],
                    }];
                } else if (numUserOnchange === 1) {
                    obj.partner_ids = _.clone(obj.partner_ids);
                    obj.partner_ids.unshift([5]);
                    obj.partner_ids[1][2].turtles.unshift([5]);
                    obj.partner_ids[2][2].turtles.unshift([5]);
                }
                numUserOnchange++;
            },
        };

        var form = await createView({
            View: FormView,
            model: 'user',
            data: this.data,
            arch: '<form><sheet><group>' +
                      '<field name="partner_ids">' +
                          '<form>'+
                              '<field name="trululu"/>' +
                              '<field name="turtles">' +
                                  '<tree editable="bottom">' +
                                      '<field name="display_name"/>' +
                                  '</tree>' +
                              '</field>' +
                          '</form>' +
                          '<tree>' +
                              '<field name="display_name"/>' +
                          '</tree>' +
                      '</field>' +
                  '</group></sheet></form>',
            res_id: 17,
        });

        // open first partner and change turtle name
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_data_row:eq(0)'));
        await testUtils.dom.click($('.modal .o_data_cell:eq(0)'));
        await testUtils.fields.editAndTrigger($('.modal input[name="display_name"]'),
            'Donatello', 'change');
        await testUtils.dom.click($('.modal .btn-primary'));

        await testUtils.dom.click(form.$('.o_data_row:eq(1)'));
        await testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));
        await testUtils.fields.editAndTrigger($('.modal input[name="display_name"]'),
            'Michelangelo', 'change');
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual(numUserOnchange, 2,
            'there should 2 and only 2 onchange from closing the partner modal');

        // check first record still has change
        await testUtils.dom.click(form.$('.o_data_row:eq(0)'));
        assert.strictEqual($('.modal .o_data_row').length, 1,
            'only 1 turtle for first partner');
        assert.strictEqual($('.modal .o_data_row').text(), 'Donatello',
            'first partner turtle is Donatello');
        await testUtils.dom.click($('.modal .o_form_button_cancel'));

        // check second record still has changes
        await testUtils.dom.click(form.$('.o_data_row:eq(1)'));
        assert.strictEqual($('.modal .o_data_row').length, 1,
            'only 1 turtle for second partner');
        assert.strictEqual($('.modal .o_data_row').text(), 'Michelangelo',
            'second partner turtle is Michelangelo');
        await testUtils.dom.click($('.modal .o_form_button_cancel'));

        form.destroy();
    });

    QUnit.test('quickly switch between pages in one2many list', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].turtles = [1, 2, 3];

        var readDefs = [Promise.resolve(), testUtils.makeTestPromise(), testUtils.makeTestPromise()];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree limit="1">' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    var recordID = args.args[0][0];
                    return Promise.resolve(readDefs[recordID - 1]).then(_.constant(result));
                }
                return result;
            },
            res_id: 1,
        });

        await testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));
        await testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

        readDefs[1].resolve();
        await testUtils.nextTick();
        assert.strictEqual(form.$('.o_field_widget[name=turtles] .o_data_cell').text(), 'donatello');

        readDefs[2].resolve();
        await testUtils.nextTick();

        assert.strictEqual(form.$('.o_field_widget[name=turtles] .o_data_cell').text(), 'raphael');

        form.destroy();
    });

    QUnit.test('many2many read, field context is properly sent', async function (assert) {
        assert.expect(4);

        this.data.partner.fields.timmy.context = {hello: 'world'};
        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'read' && args.model === 'partner_type') {
                    assert.step(args.kwargs.context.hello);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['world']);

        await testUtils.form.clickEdit(form);
        var $m2mInput = form.$('.o_field_many2manytags input');
        $m2mInput.click();
        await testUtils.nextTick();
        $m2mInput.autocomplete('widget').find('li:first()').click();
        await testUtils.nextTick();
        assert.verifySteps(['world']);

        form.destroy();
    });

    QUnit.module('FieldStatus');

    QUnit.test('static statusbar widget on many2one field', async function (assert) {
        assert.expect(5);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";
        this.data.partner.records[1].bar = false;

        var count = 0;
        var nb_fields_fetched;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                    // the following field seem useless, but its presence was the
                    // cause of a crash when evaluating the field domain.
                    '<field name="timmy" invisible="1"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read') {
                    count++;
                    nb_fields_fetched = args.kwargs.fields.length;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            config: {device: {isMobile: false}},
        });

        assert.strictEqual(count, 1, 'once search_read should have been done to fetch the relational values');
        assert.strictEqual(nb_fields_fetched, 1, 'search_read should only fetch field id');
        assert.containsN(form, '.o_statusbar_status button:not(.dropdown-toggle)', 2);
        assert.containsN(form, '.o_statusbar_status button:disabled', 2);
        assert.hasClass(form.$('.o_statusbar_status button[data-value="4"]'), 'btn-primary');
        form.destroy();
    });

    QUnit.test('static statusbar widget on many2one field with domain', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<header><field name="trululu" domain="[(\'user_id\',\'=\',uid)]" widget="statusbar"/></header>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read') {
                    assert.deepEqual(args.kwargs.domain, ['|', ['id', '=', 4], ['user_id', '=', 17]],
                        "search_read should sent the correct domain");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            session: {user_context: {uid: 17}},
        });

        form.destroy();
    });

    QUnit.test('clickable statusbar widget on many2one field', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" options=\'{"clickable": "1"}\'/></header>' +
                '</form>',
            res_id: 1,
            config: {device: {isMobile: false}},
        });


        assert.hasClass(form.$('.o_statusbar_status button[data-value="4"]'), 'btn-primary');
        assert.hasClass(form.$('.o_statusbar_status button[data-value="4"]'), 'disabled');

        assert.containsN(form, '.o_statusbar_status button.btn-secondary:not(.dropdown-toggle):not(:disabled)', 2);

        var $clickable = form.$('.o_statusbar_status button.btn-secondary:not(.dropdown-toggle):not(:disabled)');
        await testUtils.dom.click($clickable.last()); // (last is visually the first here (css))

        assert.hasClass(form.$('.o_statusbar_status button[data-value="1"]'), "btn-primary");
        assert.hasClass(form.$('.o_statusbar_status button[data-value="1"]'), "disabled");

        form.destroy();
    });

    QUnit.test('statusbar with no status', async function (assert) {
        assert.expect(2);

        this.data.product.records = [];
        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form string="Partners">
                    <header><field name="product_id" widget="statusbar"/></header>
                </form>`,
            res_id: 1,
            config: {device: {isMobile: false}},
        });

        assert.doesNotHaveClass(form.$('.o_statusbar_status'), 'o_field_empty');
        assert.strictEqual(form.$('.o_statusbar_status').children().length, 0,
            'statusbar widget should be empty');
        form.destroy();
    });

    QUnit.test('statusbar with required modifier', async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form string="Partners">
                    <header><field name="product_id" widget="statusbar" required="1"/></header>
                </form>`,
            config: {device: {isMobile: false}},
        });
        testUtils.mock.intercept(form, 'call_service', function (ev) {
            assert.strictEqual(ev.data.service, 'notification',
                "should display an 'invalid fields' notification");
        }, true);

        testUtils.form.clickSave(form);

        assert.containsOnce(form, '.o_form_editable', 'view should still be in edit');

        form.destroy();
    });

    QUnit.test('statusbar with no value in readonly', async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form>
                    <header><field name="product_id" widget="statusbar"/></header>
                </form>`,
            res_id: 1,
            config: {device: {isMobile: false}},
        });

        assert.doesNotHaveClass(form.$('.o_statusbar_status'), 'o_field_empty');
        assert.containsN(form, '.o_statusbar_status button:visible', 2);

        form.destroy();
    });

    QUnit.test('statusbar with domain but no value (create mode)', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                '</form>',
            config: {device: {isMobile: false}},
        });

        assert.containsN(form, '.o_statusbar_status button:disabled', 2);
        form.destroy();
    });

    QUnit.test('clickable statusbar should change m2o fetching domain in edit mode', async function (assert) {
        assert.expect(2);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" options=\'{"clickable": "1"}\'/></header>' +
                '</form>',
            res_id: 1,
            config: {device: {isMobile: false}},
        });

        await testUtils.form.clickEdit(form);
        assert.containsN(form, '.o_statusbar_status button:not(.dropdown-toggle)', 3);
        await testUtils.dom.click(form.$('.o_statusbar_status button:not(.dropdown-toggle)').last());
        assert.containsN(form, '.o_statusbar_status button:not(.dropdown-toggle)', 2);

        form.destroy();
    });

    QUnit.test('statusbar fold_field option and statusbar_visible attribute', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].bar = false;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" options="{\'fold_field\': \'bar\'}"/>' +
                    '<field name="color" widget="statusbar" statusbar_visible="red"/></header>' +
                '</form>',
            res_id: 1,
            config: {device: {isMobile: false}},
        });

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, '.o_statusbar_status:first .dropdown-menu button.disabled');
        assert.containsOnce(form, '.o_statusbar_status:last button.disabled');

        form.destroy();
    });

    QUnit.test('statusbar with dynamic domain', async function (assert) {
        assert.expect(5);

        this.data.partner.fields.trululu.domain = "[('int_field', '>', qux)]";
        this.data.partner.records[2].int_field = 0;

        var rpcCount = 0;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                    '<field name="qux"/>' +
                    '<field name="foo"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read') {
                    rpcCount++;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            config: {device: {isMobile: false}},
        });

        await testUtils.form.clickEdit(form);

        assert.containsN(form, '.o_statusbar_status button.disabled', 3);
        assert.strictEqual(rpcCount, 1, "should have done 1 search_read rpc");
        await testUtils.fields.editInput(form.$('input[name=qux]'), 9.5);
        assert.containsN(form, '.o_statusbar_status button.disabled', 2);
        assert.strictEqual(rpcCount, 2, "should have done 1 more search_read rpc");
        await testUtils.fields.editInput(form.$('input[name=qux]'), "hey");
        assert.strictEqual(rpcCount, 2, "should not have done 1 more search_read rpc");

        form.destroy();
    });

    // TODO: Once the code base is converted with wowl, replace webclient by formview.
    QUnit.skip('statusbar edited by the smart action "Move to stage..."', async function (assert) {
        assert.expect(3);

        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'partner,false,form': '<form>' +
                    '<header><field name="trululu" widget="statusbar" options=\'{"clickable": "1"}\'/></header>' +
                  '</form>',
            'partner,false,search': '<search></search>',
        };
        const serverData = { models: this.data, views}
        const target = getFixture();
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'partner',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        assert.containsOnce(target, ".o_field_widget")

        triggerHotkey("control+k")
        await nextTick();
        const movestage = target.querySelectorAll(".o_command");
        const idx = [...movestage].map(el => el.textContent).indexOf("Move to Trululu...ALT + SHIFT + X")
        assert.ok(idx >= 0);

        await click(movestage[idx])
        await nextTick();
        assert.deepEqual([...target.querySelectorAll(".o_command")].map(el => el.textContent), [
            "first record",
            "second record",
            "aaa",
          ])
        await click(target, "#o_command_2")
    });

    QUnit.module('FieldSelection');

    QUnit.test('widget selection in a list view', async function (assert) {
        assert.expect(3);

        this.data.partner.records.forEach(function (r) {
            r.color = 'red';
        });

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Colors" editable="top">' +
                        '<field name="color"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('td:contains(Red)').length, 3,
            "should have 3 rows with correct value");
        await testUtils.dom.click(list.$('td:contains(Red):first'));

        var $td = list.$('tbody tr.o_selected_row td:not(.o_list_record_selector)');

        assert.strictEqual($td.find('select').length, 1, "td should have a child 'select'");
        assert.strictEqual($td.contents().length, 1, "select tag should be only child of td");
        list.destroy();
    });

    QUnit.test('widget selection, edition and on many2one field', async function (assert) {
        assert.expect(21);

        this.data.partner.onchanges = {product_id: function () {}};
        this.data.partner.records[0].product_id = 37;
        this.data.partner.records[0].trululu = false;

        var count = 0;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="product_id" widget="selection"/>' +
                        '<field name="trululu" widget="selection"/>' +
                        '<field name="color" widget="selection"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                count++;
                assert.step(args.method);
                return this._super(route, args);
            },
        });

        assert.containsNone(form.$('.o_form_view'), 'select');
        assert.strictEqual(form.$('.o_field_widget[name=product_id]').text(), 'xphone',
            "should have rendered the many2one field correctly");
        assert.strictEqual(form.$('.o_field_widget[name=product_id]').attr('raw-value'), '37',
            "should have set the raw-value attr for many2one field correctly");
        assert.strictEqual(form.$('.o_field_widget[name=trululu]').text(), '',
            "should have rendered the unset many2one field correctly");
        assert.strictEqual(form.$('.o_field_widget[name=color]').text(), 'Red',
            "should have rendered the selection field correctly");
        assert.strictEqual(form.$('.o_field_widget[name=color]').attr('raw-value'), 'red',
            "should have set the raw-value attr for selection field correctly");

        await testUtils.form.clickEdit(form);

        assert.containsN(form.$('.o_form_view'), 'select', 3);
        assert.containsOnce(form, 'select[name="product_id"] option:contains(xphone)',
            "should have fetched xphone option");
        assert.containsOnce(form, 'select[name="product_id"] option:contains(xpad)',
            "should have fetched xpad option");
        assert.strictEqual(form.$('select[name="product_id"]').val(), "37",
            "should have correct product_id value");
        assert.strictEqual(form.$('select[name="trululu"]').val(), "false",
            "should not have any value in trululu field");
        await testUtils.fields.editSelect(form.$('select[name="product_id"]'), 41);

        assert.strictEqual(form.$('select[name="product_id"]').val(), "41",
            "should have a value of xphone");

        assert.strictEqual(form.$('select[name="color"]').val(), "\"red\"",
            "should have correct value in color field");

        assert.verifySteps(['read', 'name_search', 'name_search', 'onchange']);
        count = 0;
        await form.reload();
        assert.strictEqual(count, 1, "should not reload product_id relation");
        assert.verifySteps(['read']);

        form.destroy();
    });

    QUnit.test('unset selection field with 0 as key', async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists.
        assert.expect(2);

        this.data.partner.fields.selection = {
            type: "selection",
            selection: [[0, "Value O"], [1, "Value 1"]],
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="selection"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget').text(), 'Value O',
            "the displayed value should be 'Value O'");
        assert.doesNotHaveClass(form.$('.o_field_widget'), 'o_field_empty',
            "should not have class o_field_empty");

        form.destroy();
    });

    QUnit.test('unset selection field with string keys', async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists. In
        // this test, it doesn't exist as keys are strings.
        assert.expect(2);

        this.data.partner.fields.selection = {
            type: "selection",
            selection: [['0', "Value O"], ['1', "Value 1"]],
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="selection"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget').text(), '',
            "there should be no displayed value");
        assert.hasClass(form.$('.o_field_widget'),'o_field_empty',
            "should have class o_field_empty");

        form.destroy();
    });

    QUnit.test('unset selection on a many2one field', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="trululu" widget="selection"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].trululu, false,
                        "should send 'false' as trululu value");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        await testUtils.fields.editSelect(form.$('.o_form_view select'), 'false');
        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.test('field selection with many2ones and special characters', async function (assert) {
        assert.expect(1);

        // edit the partner with id=4
        this.data.partner.records[2].display_name = '<span>hey</span>';
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="trululu" widget="selection"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {mode: 'edit'},
        });
        assert.strictEqual(form.$('select option[value="4"]').text(), '<span>hey</span>');

        form.destroy();
    });

    QUnit.test('widget selection on a many2one: domain updated by an onchange', async function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {
            int_field: function () {},
        };

        var domain = [];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="int_field"/>' +
                    '<field name="trululu" widget="selection"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    domain = [['id', 'in', [10]]];
                    return Promise.resolve({
                        domain: {
                            trululu: domain,
                        }
                    });
                }
                if (args.method === 'name_search') {
                    assert.deepEqual(args.args[1], domain,
                        "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=trululu] option', 4,
            "should be 4 options in the selection");

        // trigger an onchange that will update the domain
        await testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 2);

        assert.containsOnce(form, '.o_field_widget[name=trululu] option',
            "should be 1 option in the selection");

        form.destroy();
    });

    QUnit.test('required selection widget should not have blank option', async function (assert) {
        assert.expect(12);

        this.data.partner.fields.feedback_value = {
            type: "selection",
            required: true,
            selection : [['good', 'Good'], ['bad', 'Bad']],
            default: 'good',
            string: 'Good'
        };
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="feedback_value"/>' +
                        '<field name="color" attrs="{\'required\': [(\'feedback_value\', \'=\', \'bad\')]}"/>' +
                '</form>',
            res_id: 1
        });

        await testUtils.form.clickEdit(form);

        var $colorField = form.$('.o_field_widget[name=color]');
        assert.containsN($colorField, 'option', 3, "Three options in non required field");

        assert.hasAttrValue($colorField.find('option:first()'), 'style', "",
            "Should not have display=none");
        assert.hasAttrValue($colorField.find('option:eq(1)'), 'style', "",
            "Should not have display=none");
        assert.hasAttrValue($colorField.find('option:eq(2)'), 'style', "",
            "Should not have display=none");

        const $requiredSelect = form.$('.o_field_widget[name=feedback_value]');

        assert.containsN($requiredSelect, 'option', 3, "Three options in required field");
        assert.hasAttrValue($requiredSelect.find('option:first()'), 'style', "display: none",
            "Should have display=none");
        assert.hasAttrValue($requiredSelect.find('option:eq(1)'), 'style', "",
            "Should not have display=none");
        assert.hasAttrValue($requiredSelect.find('option:eq(2)'), 'style', "",
            "Should not have display=none");

        // change value to update widget modifier values
        await testUtils.fields.editSelect($requiredSelect, '"bad"');
        $colorField = form.$('.o_field_widget[name=color]');

        assert.containsN($colorField, 'option', 3, "Three options in required field");
        assert.hasAttrValue($colorField.find('option:first()'), 'style', "display: none",
            "Should have display=none");
        assert.hasAttrValue($colorField.find('option:eq(1)'), 'style', "",
            "Should not have display=none");
        assert.hasAttrValue($colorField.find('option:eq(2)'), 'style', "",
            "Should not have display=none");

        form.destroy();
    });

    QUnit.module('FieldMany2ManyTags');

    QUnit.test('fieldmany2many tags with and without color', async function (assert) {
        assert.expect(5);

        this.data.partner.fields.partner_ids = {string: "Partner", type: "many2many", relation: 'partner'};
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="partner_ids" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method ==='read' && args.model === 'partner_type') {
                    assert.deepEqual(args.args , [[12], ['display_name']], "should not read any color field");
                } else if (args.method ==='read' && args.model === 'partner') {
                    assert.deepEqual(args.args , [[1], ['display_name', 'color']], "should read color field");
                }
                return this._super.apply(this, arguments);
            }
        });

        // add a tag on field partner_ids
        await testUtils.fields.many2one.clickOpenDropdown('partner_ids');
        await testUtils.fields.many2one.clickHighlightedItem('partner_ids');

        // add a tag on field timmy
        await testUtils.fields.many2one.clickOpenDropdown('timmy');
        var $input = form.$('.o_field_many2manytags[name="timmy"] input');
        assert.strictEqual($input.autocomplete('widget').find('li').length, 3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')");
        await testUtils.fields.many2one.clickHighlightedItem('timmy');
        assert.containsOnce(form, '.o_field_many2manytags[name="timmy"] .badge',
            "should contain 1 tag");
        assert.containsOnce(form, '.o_field_many2manytags[name="timmy"] .badge:contains("gold")',
            "should contain newly added tag 'gold'");

        form.destroy();
    });

    QUnit.test('fieldmany2many tags with color: rendering and edition', async function (assert) {
        assert.expect(28);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records.push({id: 13, display_name: "red", color: 8});
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\', \'no_create_edit\': True}"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    var commands = args.args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(commands[0][0], 6, "generated command should be REPLACE WITH");
                    assert.ok(_.isEqual(_.sortBy(commands[0][2], _.identity.bind(_)), [12, 13]),
                        "new value should be [12, 13]");
                }
                if (args.method ==='read' && args.model === 'partner_type') {
                    assert.deepEqual(args.args[1], ['display_name', 'color'], "should read the color field");
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.containsN(form, '.o_field_many2manytags .badge .dropdown-toggle', 2,
            "should contain 2 tags");
        assert.ok(form.$('.badge .dropdown-toggle:contains(gold)').length,
            'should have fetched and rendered gold partner tag');
        assert.ok(form.$('.badge .dropdown-toggle:contains(silver)').length,
            'should have fetched and rendered silver partner tag');
        assert.strictEqual(form.$('.badge:first()').data('color'), 2,
            'should have correctly fetched the color');

        await testUtils.form.clickEdit(form);

        assert.containsN(form, '.o_field_many2manytags .badge .dropdown-toggle', 2,
            "should still contain 2 tags in edit mode");
        assert.ok(form.$('.o_tag_color_2 .o_badge_text:contains(gold)').length,
            'first tag should still contain "gold" and be color 2 in edit mode');
        assert.containsN(form, '.o_field_many2manytags .o_delete', 2,
            "tags should contain a delete button");

        // add an other existing tag
        var $input = form.$('.o_field_many2manytags input');
        await testUtils.fields.many2one.clickOpenDropdown('timmy');
        assert.strictEqual($input.autocomplete('widget').find('li').length, 2,
            "autocomplete dropdown should have 2 entry");
        assert.strictEqual($input.autocomplete('widget').find('li a:contains("red")').length, 1,
            "autocomplete dropdown should contain 'red'");
        await testUtils.fields.many2one.clickHighlightedItem('timmy');
        assert.containsN(form, '.o_field_many2manytags .badge .dropdown-toggle', 3,
            "should contain 3 tags");
        assert.ok(form.$('.o_field_many2manytags .badge .dropdown-toggle:contains("red")').length,
            "should contain newly added tag 'red'");
        assert.ok(form.$('.o_field_many2manytags .badge[data-color=8] .dropdown-toggle:contains("red")').length,
            "should have fetched the color of added tag");

        // remove tag with id 14
        await testUtils.dom.click(form.$('.o_field_many2manytags .badge[data-id=14] .o_delete'));
        assert.containsN(form, '.o_field_many2manytags .badge .dropdown-toggle', 2,
            "should contain 2 tags");
        assert.ok(!form.$('.o_field_many2manytags .badge .dropdown-toggle:contains("silver")').length,
            "should not contain tag 'silver' anymore");

        // save the record (should do the write RPC with the correct commands)
        await testUtils.form.clickSave(form);

        // checkbox 'Hide in Kanban'
        $input = form.$('.o_field_many2manytags .badge[data-id=13] .dropdown-toggle'); // selects 'red' tag
        await testUtils.dom.click($input);
        var $checkBox = form.$('.o_field_many2manytags .badge[data-id=13] .custom-checkbox input');
        assert.strictEqual($checkBox.length, 1, "should have a checkbox in the colorpicker dropdown menu");
        assert.notOk($checkBox.is(':checked'), "should have unticked checkbox in colorpicker dropdown menu");

        await testUtils.fields.editAndTrigger($checkBox, null,['mouseenter','mousedown']);

        $input = form.$('.o_field_many2manytags .badge[data-id=13] .dropdown-toggle'); // refresh
        await testUtils.dom.click($input);
        $checkBox = form.$('.o_field_many2manytags .badge[data-id=13] .custom-checkbox input'); // refresh
        assert.equal($input.parent().data('color'), "0", "should become transparent when toggling on checkbox");
        assert.ok($checkBox.is(':checked'), "should have a ticked checkbox in colorpicker dropdown menu after mousedown");

        await testUtils.fields.editAndTrigger($checkBox, null,['mouseenter','mousedown']);

        $input = form.$('.o_field_many2manytags .badge[data-id=13] .dropdown-toggle'); // refresh
        await testUtils.dom.click($input);
        $checkBox = form.$('.o_field_many2manytags .badge[data-id=13] .custom-checkbox input'); // refresh
        assert.equal($input.parent().data('color'), "8", "should revert to old color when toggling off checkbox");
        assert.notOk($checkBox.is(':checked'), "should have an unticked checkbox in colorpicker dropdown menu after 2nd click");

        // TODO: it would be nice to test the behaviors of the autocomplete dropdown
        // (like refining the research, creating new tags...), but ui-autocomplete
        // makes it difficult to test
        form.destroy();
    });

    QUnit.test('fieldmany2many tags in tree view', async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].timmy = [12, 14];
        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Partners">' +
                '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                '</tree>',
        });
        assert.containsN(list, '.o_field_many2manytags .badge', 2, "there should be 2 tags");
        assert.containsNone(list, '.badge.dropdown-toggle', "the tags should not be dropdowns");

        testUtils.mock.intercept(list, 'switch_view', function (event) {
            assert.strictEqual(event.data.view_type, "form", "should switch to form view");
        });
        // click on the tag: should do nothing and open the form view
        testUtils.dom.click(list.$('.o_field_many2manytags .badge:first'));

        list.destroy();
    });

    QUnit.test('fieldmany2many tags view a domain', async function (assert) {
        assert.expect(7);

        this.data.partner.fields.timmy.domain = [['id', '<', 50]];
        this.data.partner.records[0].timmy = [12];
        this.data.partner_type.records.push({id: 99, display_name: "red", color: 8});

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'no_create_edit\': True}"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, [['id', '<', 50], ['id', 'not in', [12]]],
                        "domain sent to name_search should be correct");
                    return Promise.resolve([[14, 'silver']]);
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.containsOnce(form, '.o_field_many2manytags .badge',
            "should contain 1 tag");
        assert.ok(form.$('.badge:contains(gold)').length,
            'should have fetched and rendered gold partner tag');

        await testUtils.form.clickEdit(form);

        // add an other existing tag
        var $input = form.$('.o_field_many2manytags input');
        await testUtils.fields.many2one.clickOpenDropdown('timmy');
        assert.strictEqual($input.autocomplete('widget').find('li').length, 2,
        "autocomplete dropdown should have 2 entry");
        assert.strictEqual($input.autocomplete('widget').find('li a:contains("silver")').length, 1,
        "autocomplete dropdown should contain 'silver'");
        await testUtils.fields.many2one.clickHighlightedItem('timmy');
        assert.containsN(form, '.o_field_many2manytags .badge', 2,
            "should contain 2 tags");
        assert.ok(form.$('.o_field_many2manytags .badge:contains("silver")').length,
            "should contain newly added tag 'silver'");

        form.destroy();
    });

    QUnit.test('fieldmany2many tags in a new record', async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/create') {
                    var commands = args.args[0].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(commands[0][0], 6, "generated command should be REPLACE WITH");
                    assert.ok(_.isEqual(commands[0][2], [12]), "new value should be [12]");
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.hasClass(form.$('.o_form_view'),'o_form_editable', "form should be in edit mode");

        await testUtils.fields.many2one.clickOpenDropdown('timmy');
        assert.strictEqual(form.$('.o_field_many2manytags input').autocomplete('widget').find('li').length, 3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')");
        await testUtils.fields.many2one.clickHighlightedItem('timmy');

        assert.containsOnce(form, '.o_field_many2manytags .badge',
            "should contain 1 tag");
        assert.ok(form.$('.o_field_many2manytags .badge:contains("gold")').length,
            "should contain newly added tag 'gold'");

        // save the record (should do the write RPC with the correct commands)
        await testUtils.form.clickSave(form);
        form.destroy();
    });

    QUnit.test('fieldmany2many tags: update color', async function (assert) {
        assert.expect(5);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records[0].color = 0;

        var color;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {color: color},
                        "shoud write the new color");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        // First checks that default color 0 is rendered as 0 color
        assert.ok(form.$('.badge.dropdown:first()').is('.o_tag_color_0'),
            'first tag color should be 0');

        // Update the color in readonly
        color = 1;
        await testUtils.dom.click(form.$('.badge:first() .dropdown-toggle'));
        await testUtils.dom.triggerEvents($('.o_colorpicker a[data-color="' + color + '"]'), ['mousedown']);
        await testUtils.nextTick();
        assert.strictEqual(form.$('.badge:first()').data('color'), color,
            'should have correctly updated the color (in readonly)');

        // Update the color in edit
        color = 6;
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.badge:first() .dropdown-toggle'));
        await testUtils.dom.triggerEvents($('.o_colorpicker a[data-color="' + color + '"]'), ['mousedown']); // choose color 6
        await testUtils.nextTick();
        assert.strictEqual(form.$('.badge:first()').data('color'), color,
            'should have correctly updated the color (in edit)');

        form.destroy();
    });

    QUnit.test('fieldmany2many tags with no_edit_color option', async function (assert) {
        assert.expect(1);

        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\', \'no_edit_color\': 1}"/>' +
                '</form>',
            res_id: 1,
        });

        // Click to try to open colorpicker
        await testUtils.dom.click(form.$('.badge:first() .dropdown-toggle'));
        assert.containsNone(document.body, '.o_colorpicker');

        form.destroy();
    });

    QUnit.test('fieldmany2many tags in editable list', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            context: {take: 'five'},
            arch:'<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'read' && args.model === 'partner_type') {
                    assert.deepEqual(args.kwargs.context, {take: 'five'},
                        'The context should be passed to the RPC');
                }
            return this._super.apply(this, arguments);
            }
        });

        assert.containsOnce(list, '.o_data_row:first .o_field_many2manytags .badge',
            "m2m field should contain one tag");

        // edit first row
        await testUtils.dom.click(list.$('.o_data_row:first td:nth(2)'));

        var $m2o = list.$('.o_data_row:first .o_field_many2manytags .o_field_many2one');
        assert.strictEqual($m2o.length, 1, "a many2one widget should have been instantiated");

        // add a tag
        await testUtils.fields.many2one.clickOpenDropdown('timmy');
        await testUtils.fields.many2one.clickHighlightedItem('timmy');

        assert.containsN(list, '.o_data_row:first .o_field_many2manytags .badge', 2,
            "m2m field should contain 2 tags");

        // leave edition
        await testUtils.dom.click(list.$('.o_data_row:nth(1) td:nth(2)'));

        assert.containsN(list, '.o_data_row:first .o_field_many2manytags .badge', 2,
            "m2m field should contain 2 tags");

        list.destroy();
    });

    QUnit.test('search more in many2one: group and use the pager', async function (assert) {
        assert.expect(2);

        this.data.partner.records.push({
            id: 5,
            display_name: "Partner 4",
        }, {
            id: 6,
            display_name: "Partner 5",
        }, {
            id: 7,
            display_name: "Partner 6",
        }, {
            id: 8,
            display_name: "Partner 7",
        }, {
            id: 9,
            display_name: "Partner 8",
        }, {
            id: 10,
            display_name: "Partner 9",
        });
        this.data.partner.fields.datetime.searchable = true;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',

            res_id: 1,
            archs: {
                'partner,false,list': '<tree limit="7"><field name="display_name"/></tree>',
                'partner,false,search': '<search><group>' +
                       '    <filter name="bar" string="Bar" context="{\'group_by\': \'bar\'}"/>' +
                        '</group></search>',
            },
            viewOptions: {
                mode: 'edit',
            },
        });
        await testUtils.fields.many2one.clickOpenDropdown('trululu');
        await testUtils.fields.many2one.clickItem('trululu', 'Search');
        const modal = document.body.querySelector(".modal");
        await cpHelpers.toggleGroupByMenu(modal);
        await cpHelpers.toggleMenuItem(modal, "Bar");

        await testUtils.dom.click($('.modal .o_group_header:first'));

        assert.strictEqual($('.modal tbody:nth(1) .o_data_row').length, 7,
            "should display 7 records in the first page");
        await testUtils.dom.click($('.modal .o_group_header:first .o_pager_next'));
        assert.strictEqual($('.modal tbody:nth(1) .o_data_row').length, 1,
            "should display 1 record in the second page");

        form.destroy();
    });

    QUnit.test('many2many_tags can load more than 40 records', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.partner_ids = {string: "Partner", type: "many2many", relation: 'partner'};
        this.data.partner.records[0].partner_ids = [];
        for (var i = 15; i < 115; i++) {
            this.data.partner.records.push({id: i, display_name: 'walter' + i});
            this.data.partner.records[0].partner_ids.push(i);
        }
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                '</form>',
            res_id: 1,
        });
        assert.containsN(form, '.o_field_widget[name="partner_ids"] .badge', 100,
            'should have rendered 100 tags');
        form.destroy();
    });

    QUnit.test('many2many_tags loads records according to limit defined on widget prototype', async function (assert) {
        assert.expect(1);

        const M2M_LIMIT = relationalFields.FieldMany2ManyTags.prototype.limit;
        relationalFields.FieldMany2ManyTags.prototype.limit = 30;
        this.data.partner.fields.partner_ids = {string: "Partner", type: "many2many", relation: 'partner'};
        this.data.partner.records[0].partner_ids = [];
        for (var i = 15; i < 50; i++) {
            this.data.partner.records.push({id: i, display_name: 'walter' + i});
            this.data.partner.records[0].partner_ids.push(i);
        }
        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge').length, 30,
            'should have rendered 30 tags even though 35 records linked');

        relationalFields.FieldMany2ManyTags.prototype.limit = M2M_LIMIT;
        form.destroy();
    });

    QUnit.test('field many2many_tags keeps focus when being edited', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];
        this.data.partner.onchanges.foo = function (obj) {
            obj.timmy = [[5]]; // DELETE command
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_many2manytags .badge',
            "should contain one tag");

        // update foo, which will trigger an onchange and update timmy
        // -> m2mtags input should not have taken the focus
        form.$('input[name=foo]').focus();
        await testUtils.fields.editInput(form.$('input[name=foo]'), 'trigger onchange');
        assert.containsNone(form, '.o_field_many2manytags .badge',
            "should contain no tags");
        assert.strictEqual(form.$('input[name=foo]').get(0), document.activeElement,
            "foo input should have kept the focus");

        // add a tag -> m2mtags input should still have the focus
        await testUtils.fields.many2one.clickOpenDropdown('timmy');
        await testUtils.fields.many2one.clickHighlightedItem('timmy');


        assert.containsOnce(form, '.o_field_many2manytags .badge',
            "should contain a tag");
        assert.strictEqual(form.$('.o_field_many2manytags input').get(0), document.activeElement,
            "m2m tags input should have kept the focus");

        // remove a tag -> m2mtags input should still have the focus
        await testUtils.dom.click(form.$('.o_field_many2manytags .o_delete'));
        assert.containsNone(form, '.o_field_many2manytags .badge',
            "should contain no tags");
        assert.strictEqual(form.$('.o_field_many2manytags input').get(0), document.activeElement,
            "m2m tags input should have kept the focus");

        form.destroy();
    });

    QUnit.test('widget many2many_tags in one2many with display_name', async function (assert) {
        assert.expect(4);
        this.data.turtle.records[0].partner_ids = [2];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="turtles">' +
                            '<tree>' +
                                '<field name="partner_ids" widget="many2many_tags"/>' +  // will use display_name
                            '</tree>' +
                            '<form>' +
                                '<sheet>' +
                                    '<field name="partner_ids"/>' +
                                '</sheet>' +
                            '</form>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,list': '<tree><field name="foo"/></tree>',
            },
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_one2many[name="turtles"] .o_list_view .o_field_many2manytags[name="partner_ids"]').text().replace(/\s/g, ''),
            "secondrecordaaa", "the tags should be correctly rendered");

        // open the x2m form view
        await testUtils.dom.click(form.$('.o_field_one2many[name="turtles"] .o_list_view td.o_data_cell:first'));
        await testUtils.nextTick(); // wait for quick edit
        assert.strictEqual($('.modal .o_form_view .o_field_many2many[name="partner_ids"] .o_list_view .o_data_cell').text(),
            "blipMy little Foo Value", "the list view should be correctly rendered with foo");

        await testUtils.dom.click($('.modal button.o_form_button_cancel'));
        assert.strictEqual(form.$('.o_field_one2many[name="turtles"] .o_list_view .o_field_many2manytags[name="partner_ids"]').text().replace(/\s/g, ''),
            "secondrecordaaa", "the tags should still be correctly rendered");

        assert.strictEqual(form.$('.o_field_one2many[name="turtles"] .o_list_view .o_field_many2manytags[name="partner_ids"]').text().replace(/\s/g, ''),
            "secondrecordaaa", "the tags should still be correctly rendered");

        form.destroy();
    });

    QUnit.test('widget many2many_tags: tags title attribute', async function (assert) {
        assert.expect(1);
        this.data.turtle.records[0].partner_ids = [2];

        var form = await createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch:'<form string="Turtles">' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                        '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.deepEqual(
            form.$('.o_field_many2manytags.o_field_widget .badge .o_badge_text').attr('title'),
            'second record', 'the title should be filled in'
        );

        form.destroy();
    });

    QUnit.test('widget many2many_tags: toggle colorpicker multiple times', async function (assert) {
        assert.expect(11);

        this.data.partner.records[0].timmy = [12];
        this.data.partner_type.records[0].color = 0;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual($('.o_field_many2manytags .badge').length, 1,
            "should have one tag");
        assert.strictEqual($('.o_field_many2manytags .badge').data('color'), 0,
            "tag should have color 0");
        assert.strictEqual($('.o_colorpicker:visible').length, 0,
            "colorpicker should be closed");

        // click on the badge to open colorpicker
        await testUtils.dom.click(form.$('.o_field_many2manytags .badge .dropdown-toggle'));

        assert.strictEqual($('.o_colorpicker:visible').length, 1,
            "colorpicker should be open");

        // click on the badge again to close colorpicker
        await testUtils.dom.click(form.$('.o_field_many2manytags .badge .dropdown-toggle'));

        assert.strictEqual($('.o_field_many2manytags .badge').data('color'), 0,
            "tag should still have color 0");
        assert.strictEqual($('.o_colorpicker:visible').length, 0,
            "colorpicker should be closed");

        // click on the badge to open colorpicker
        await testUtils.dom.click(form.$('.o_field_many2manytags .badge .dropdown-toggle'));

        assert.strictEqual($('.o_colorpicker:visible').length, 1,
            "colorpicker should be open");

        // click on the colorpicker, but not on a color
        await testUtils.dom.click(form.$('.o_colorpicker'));

        assert.strictEqual($('.o_field_many2manytags .badge').data('color'), 0,
            "tag should still have color 0");
        assert.strictEqual($('.o_colorpicker:visible').length, 0,
            "colorpicker should be closed");

        // click on the badge to open colorpicker
        await testUtils.dom.click(form.$('.o_field_many2manytags .badge .dropdown-toggle'));

        // click on a color in the colorpicker
        await testUtils.dom.triggerEvents(form.$('.o_colorpicker .o_tag_color_2'),['mousedown']);

        assert.strictEqual($('.o_field_many2manytags .badge').data('color'), 2,
            "tag should have color 2");
        assert.strictEqual($('.o_colorpicker:visible').length, 0,
            "colorpicker should be closed");

        form.destroy();
    });

    QUnit.test('widget many2many_tags_avatar', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="partner_ids" widget="many2many_tags_avatar"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.containsN(form, '.o_field_many2manytags.avatar.o_field_widget .badge', 2, "should have 2 records");
        assert.strictEqual(form.$('.o_field_many2manytags.avatar.o_field_widget .badge:first img').data('src'), '/web/image/partner/2/avatar_128',
            "should have correct avatar image");

        form.destroy();
    });

    QUnit.test('widget many2many_tags_avatar in list view', async function (assert) {
        assert.expect(18);

        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        this.data.partner.records = this.data.partner.records.concat(records);

        this.data.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        this.data.turtle.records[0].partner_ids = [1];
        this.data.turtle.records[1].partner_ids = [1, 2, 4, 5, 6, 7];
        this.data.turtle.records[2].partner_ids = [1, 2, 4, 5, 7];

        const list = await createView({
            View: ListView,
            model: 'turtle',
            data: this.data,
            arch: '<tree editable="bottom"><field name="partner_ids" widget="many2many_tags_avatar"/></tree>',
        });

        assert.strictEqual(list.$('.o_data_row:first .o_field_many2manytags img.o_m2m_avatar').data('src'),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(list.$('.o_data_row:first .o_many2many_tags_avatar_cell .o_field_many2manytags div').text().trim(),
            "first record",
            "should display like many2one avatar if there is only one record");

        assert.containsN(list, '.o_data_row:eq(1) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)', 4,
            "should have 4 records");
        assert.containsN(list, '.o_data_row:eq(2) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)', 5,
            "should have 5 records");
        assert.containsOnce(list, '.o_data_row:eq(1) .o_field_many2manytags .o_m2m_avatar_empty',
            "should have o_m2m_avatar_empty span");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_many2manytags .o_m2m_avatar_empty').text().trim(), "+2",
            "should have +2 in o_m2m_avatar_empty");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:first').data('src'),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:eq(1)').data('src'),
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:eq(2)').data('src'),
            "/web/image/partner/4/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:eq(3)').data('src'),
            "/web/image/partner/5/avatar_128",
            "should have correct avatar image");
        assert.containsNone(list, '.o_data_row:eq(2) .o_field_many2manytags .o_m2m_avatar_empty',
            "should have o_m2m_avatar_empty span");
        assert.containsN(list, '.o_data_row:eq(3) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)', 4,
            "should have 4 records");
        assert.containsOnce(list, '.o_data_row:eq(3) .o_field_many2manytags .o_m2m_avatar_empty',
            "should have o_m2m_avatar_empty span");
        assert.strictEqual(list.$('.o_data_row:eq(3) .o_field_many2manytags .o_m2m_avatar_empty').text().trim(), "+9",
            "should have +9 in o_m2m_avatar_empty");

        list.$('.o_data_row:eq(1) .o_field_many2manytags .o_m2m_avatar_empty').trigger($.Event('mouseenter'));
        await testUtils.nextTick();
        assert.containsOnce(list, '.popover',
            "should open a popover hover on o_m2m_avatar_empty");
        assert.strictEqual(list.$('.popover .popover-body > div').text().trim(), "record 6record 7",
            "should have a right text in popover");

        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_many2many_tags_avatar_cell'));
        assert.containsN(list, '.o_data_row.o_selected_row .o_many2many_tags_avatar_cell .badge', 1,
            "should have 1 many2many badges in edit mode");

        await testUtils.fields.many2one.clickOpenDropdown('partner_ids');
        await testUtils.fields.many2one.clickItem('partner_ids', 'second record');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsN(list, '.o_data_row:eq(0) .o_field_many2manytags span', 2,
            "should have 2 records");

        list.destroy();
    });

    QUnit.test('widget many2many_tags_avatar in kanban view', async function (assert) {
        assert.expect(13);

        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        this.data.partner.records = this.data.partner.records.concat(records);

        this.data.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        this.data.turtle.records[0].partner_ids = [1];
        this.data.turtle.records[1].partner_ids = [1, 2, 4];
        this.data.turtle.records[2].partner_ids = [1, 2, 4, 5];

        const kanban = await createView({
            View: KanbanView,
            model: 'turtle',
            data: this.data,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'turtle,false,form': '<form><field name="display_name"/></form>',
            },
            intercepts: {
                switch_view: function (event) {
                    const { mode, model, res_id, view_type } = event.data;
                    assert.deepEqual({ mode, model, res_id, view_type }, {
                        mode: 'readonly',
                        model: 'turtle',
                        res_id: 1,
                        view_type: 'form',
                    }, "should trigger an event to open the clicked record in a form view");
                },
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_record:first .o_field_many2manytags img.o_m2m_avatar').data('src'),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image");

        assert.containsN(kanban, '.o_kanban_record:eq(1) .o_field_many2manytags span', 3,
            "should have 3 records");
        assert.containsN(kanban, '.o_kanban_record:eq(2) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)', 2,
            "should have 2 records");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags img.o_m2m_avatar:first').data('src'),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags img.o_m2m_avatar:eq(1)').data('src'),
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image");
        assert.containsOnce(kanban, '.o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty',
            "should have o_m2m_avatar_empty span");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty').text().trim(), "+2",
            "should have +2 in o_m2m_avatar_empty");

        assert.containsN(kanban, '.o_kanban_record:eq(3) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)', 2,
            "should have 2 records");
        assert.containsOnce(kanban, '.o_kanban_record:eq(3) .o_field_many2manytags .o_m2m_avatar_empty',
            "should have o_m2m_avatar_empty span");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(3) .o_field_many2manytags .o_m2m_avatar_empty').text().trim(), "9+",
            "should have 9+ in o_m2m_avatar_empty");

        kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty').trigger($.Event('mouseenter'));
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.popover',
            "should open a popover hover on o_m2m_avatar_empty");
        assert.strictEqual(kanban.$('.popover .popover-body > div').text().trim(), "aaarecord 5",
            "should have a right text in popover");
        await testUtils.dom.click(kanban.$('.o_kanban_record:first .o_field_many2manytags img.o_m2m_avatar'));

        kanban.destroy();
    });

    QUnit.test('fieldmany2many tags: quick create a new record', async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form><field name="timmy" widget="many2many_tags"/></form>`,
        });

        assert.containsNone(form, '.o_field_many2manytags .badge');

        await testUtils.fields.many2one.searchAndClickItem('timmy', {search: 'new value'});

        assert.containsOnce(form, '.o_field_many2manytags .badge');

        await testUtils.form.clickSave(form);

        assert.strictEqual(form.el.querySelector('.o_field_many2manytags').innerText.trim(), "new value");

        form.destroy();
    });

    QUnit.test("select a many2many value by focusing out", async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form><field name="timmy" widget="many2many_tags"/></form>`,
        });

        assert.containsNone(form, '.o_field_many2manytags .badge');

        form.$('.o_field_many2manytags input').focus().val('go').trigger('input').trigger('keyup');
        await testUtils.nextTick();
        form.$('.o_field_many2manytags input').trigger('blur');
        await testUtils.nextTick();

        assert.containsNone(document.body, '.modal');
        assert.containsOnce(form, '.o_field_many2manytags .badge');
        assert.strictEqual(form.$('.o_field_many2manytags .badge').text().trim(), 'gold');

        form.destroy();
    });

    QUnit.module('FieldRadio');

    QUnit.test('fieldradio widget on a many2one in a new record', async function (assert) {
        assert.expect(6);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="product_id" widget="radio"/>' +
                '</form>',
        });

        assert.ok(form.$('div.o_radio_item').length, "should have rendered outer div");
        assert.containsN(form, 'input.o_radio_input', 2, "should have 2 possible choices");
        assert.ok(form.$('label.o_form_label:contains(xphone)').length, "one of them should be xphone");
        assert.containsNone(form, 'input:checked', "none of the input should be checked");

        await testUtils.dom.click(form.$("input.o_radio_input:first"));

        assert.containsOnce(form, 'input:checked', "one of the input should be checked");

        await testUtils.form.clickSave(form);

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.product_id, 37, "should have saved record with correct value");
        form.destroy();
    });

    QUnit.test('required fieldradio widget on a many2one', async function (assert) {
        assert.expect(6);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                '<field name="product_id" widget="radio" required="1"/>' +
                '</form>',
        });

        testUtils.mock.intercept(form, 'call_service', function (event) {
            if (event.data.service === 'notification' && event.data.method === 'notify') {
                assert.step('danger');
                assert.equal(event.data.args[0].type, 'danger');
                assert.equal(event.data.args[0].title, 'Invalid fields:');
                assert.equal(event.data.args[0].message, '<ul><li>Product</li></ul>');
            }
        });

        assert.containsNone(form, 'input:checked', "none of the input should be checked");

        await testUtils.form.clickSave(form);
        assert.verifySteps(['danger']);
        form.destroy();
    });

    QUnit.test('fieldradio change value by onchange', async function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {bar: function (obj) {
            obj.product_id = obj.bar ? 41 : 37;
            obj.color = obj.bar ? 'red' : 'black';
        }};

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="bar"/>' +
                    '<field name="product_id" widget="radio"/>' +
                    '<field name="color" widget="radio"/>' +
                '</form>',
        });

        await testUtils.dom.click(form.$("input[type='checkbox']"));
        assert.containsOnce(form, 'input.o_radio_input[data-value="37"]:checked', "one of the input should be checked");
        assert.containsOnce(form, 'input.o_radio_input[data-value="black"]:checked', "the other of the input should be checked");
        await testUtils.dom.click(form.$("input[type='checkbox']"));
        assert.containsOnce(form, 'input.o_radio_input[data-value="41"]:checked', "the other of the input should be checked");
        assert.containsOnce(form, 'input.o_radio_input[data-value="red"]:checked', "one of the input should be checked");

        form.destroy();
    });

    QUnit.test('fieldradio widget on a selection in a new record', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="color" widget="radio"/>' +
                '</form>',
        });


        assert.ok(form.$('div.o_radio_item').length, "should have rendered outer div");
        assert.containsN(form, 'input.o_radio_input', 2, "should have 2 possible choices");
        assert.ok(form.$('label.o_form_label:contains(Red)').length, "one of them should be Red");

        // click on 2nd option
        await testUtils.dom.click(form.$("input.o_radio_input").eq(1));

        await testUtils.form.clickSave(form);

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.color, 'black', "should have saved record with correct value");
        form.destroy();
    });

    QUnit.test('fieldradio widget has o_horizontal or o_vertical class', async function (assert) {
        assert.expect(2);

        this.data.partner.fields.color2 = this.data.partner.fields.color;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                    '<field name="color" widget="radio"/>' +
                    '<field name="color2" widget="radio" options="{\'horizontal\': True}"/>' +
                    '</group>' +
                '</form>',
        });

        var btn1 = form.$('div.o_field_radio.o_vertical');
        var btn2 = form.$('div.o_field_radio.o_horizontal');

        assert.strictEqual(btn1.length, 1, "should have o_vertical class");
        assert.strictEqual(btn2.length, 1, "should have o_horizontal class");
        form.destroy();
    });

    QUnit.test('fieldradio widget with numerical keys encoded as strings', async function (assert) {
        assert.expect(7);

        this.data.partner.fields.selection = {
            type: 'selection',
            selection: [['0', "Red"], ['1', "Black"]],
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="selection" widget="radio"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].selection, '1',
                        "should write correct value");
                }
                return this._super.apply(this, arguments);
            },
        });


        assert.strictEqual(form.$('.o_field_widget').text().trim().split(/\s+/g).join(','), 'Red,Black');
        assert.containsNone(form, '.o_radio_input:checked', "no value should be checked");

        await testUtils.form.clickEdit(form);

        assert.containsNone(form, '.o_radio_input:checked',
            "no value should be checked");

        await testUtils.dom.click(form.$("input.o_radio_input:nth(1)"));

        await testUtils.form.clickSave(form);

        assert.strictEqual(form.$('.o_field_widget').text().trim().split(/\s+/g).join(','), 'Red,Black');
        assert.containsOnce(form, '.o_radio_input[data-index=1]:checked',
            "'Black' should be checked");

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, '.o_radio_input[data-index=1]:checked',
            "'Black' should be checked");

        form.destroy();
    });

    QUnit.test('widget radio on a many2one: domain updated by an onchange', async function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {
            int_field: function () {},
        };

        var domain = [];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="int_field"/>' +
                    '<field name="trululu" widget="radio"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    domain = [['id', 'in', [10]]];
                    return Promise.resolve({
                        value: {
                            trululu: false,
                        },
                        domain: {
                            trululu: domain,
                        },
                    });
                }
                if (args.method === 'search_read') {
                    assert.deepEqual(args.kwargs.domain, domain,
                        "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=trululu] .o_radio_item', 3,
            "should be 3 radio buttons");

        // trigger an onchange that will update the domain
        await testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 2);
        assert.containsNone(form, '.o_field_widget[name=trululu] .o_radio_item',
            "should be no more radio button");

        form.destroy();
    });


    QUnit.module('FieldSelectionBadge');

    QUnit.test('FieldSelectionBadge widget on a many2one in a new record', async function (assert) {
        assert.expect(6);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="product_id" widget="selection_badge"/>' +
                '</form>',
        });

        assert.ok(form.$('span.o_selection_badge').length, "should have rendered outer div");
        assert.containsN(form, 'span.o_selection_badge', 2, "should have 2 possible choices");
        assert.ok(form.$('span.o_selection_badge:contains(xphone)').length, "one of them should be xphone");
        assert.containsNone(form, 'span.active', "none of the input should be checked");

        await testUtils.dom.click($("span.o_selection_badge:first"));

        assert.containsOnce(form, 'span.active', "one of the input should be checked");

        await testUtils.form.clickSave(form);

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.product_id, 37, "should have saved record with correct value");
        form.destroy();
    });

    QUnit.test('FieldSelectionBadge widget on a selection in a new record', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="color" widget="selection_badge"/>' +
                '</form>',
        });

        assert.ok(form.$('span.o_selection_badge').length, "should have rendered outer div");
        assert.containsN(form, 'span.o_selection_badge', 2, "should have 2 possible choices");
        assert.ok(form.$('span.o_selection_badge:contains(Red)').length, "one of them should be Red");

        // click on 2nd option
        await testUtils.dom.click(form.$("span.o_selection_badge").eq(1));

        await testUtils.form.clickSave(form);

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.color, 'black', "should have saved record with correct value");
        form.destroy();
    });

    QUnit.test('FieldSelectionBadge widget on a selection in a readonly mode', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="color" widget="selection_badge" readonly="1"/>' +
                '</form>',
        });

        assert.containsOnce(form, 'span.o_readonly_modifier', "should have 1 possible value in readonly mode");
        form.destroy();
    });

    QUnit.module('FieldSelectionFont');

    QUnit.test('FieldSelectionFont displays the correct fonts on options', async function (assert) {
        assert.expect(4);

        this.data.partner.fields.fonts = {
            type: "selection",
            selection: [['Lato', "Lato"], ['Oswald', "Oswald"]],
            default: 'Lato',
            string: "Fonts",
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="fonts" widget="font"/>' +
                '</form>',
        });
        var options = form.$('.o_field_widget[name="fonts"] > option');

        assert.strictEqual(form.$('.o_field_widget[name="fonts"]').css('fontFamily'), 'Lato',
            "Widget font should be default (Lato)");
        assert.strictEqual($(options[0]).css('fontFamily'), 'Lato',
            "Option 0 should have the correct font (Lato)");
        assert.strictEqual($(options[1]).css('fontFamily'), 'Oswald',
            "Option 1 should have the correct font (Oswald)");

        await testUtils.fields.editSelect(form.$('.o_field_widget[name="fonts"]'), '"Oswald"');
        assert.strictEqual(form.$('.o_field_widget[name="fonts"]').css('fontFamily'), 'Oswald',
            "Widget font should be updated (Oswald)");

        form.destroy();
    });

    QUnit.module('FieldMany2ManyCheckBoxes');

    QUnit.test('widget many2many_checkboxes', async function (assert) {
        assert.expect(10);

        this.data.partner.records[0].timmy = [12];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<group><field name="timmy" widget="many2many_checkboxes"/></group>' +
                '</form>',
            res_id: 1,
        });

        assert.containsN(form, 'div.o_field_widget div.custom-checkbox', 2,
            "should have fetched and displayed the 2 values of the many2many");

        assert.ok(form.$('div.o_field_widget div.custom-checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').prop('disabled'),
            "the checkboxes should not be disabled");

        await testUtils.form.clickEdit(form);

        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').prop('disabled'),
            "the checkboxes should not be disabled");

        // add a m2m value by clicking on input
        await testUtils.dom.click(form.$('div.o_field_widget div.custom-checkbox input').eq(1));
        await testUtils.form.clickSave(form);
        assert.deepEqual(this.data.partner.records[0].timmy, [12, 14],
            "should have added the second element to the many2many");
        assert.containsN(form, 'input:checked', 2,
            "both checkboxes should be checked");

        // remove a m2m value by clinking on label
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('div.o_field_widget div.custom-checkbox > label').eq(0));
        await testUtils.form.clickSave(form);
        assert.deepEqual(this.data.partner.records[0].timmy, [14],
            "should have removed the first element to the many2many");
        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.ok(form.$('div.o_field_widget div.custom-checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes (readonly)', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form string="Partners">
                    <group>
                        <field name="timmy" widget="many2many_checkboxes"
                            attrs="{'readonly': true}"/>
                    </group>
                </form>`,
            res_id: 1,
        });

        assert.containsN(form, 'div.o_field_widget div.custom-checkbox', 2,
            "should have fetched and displayed the 2 values of the many2many");

        assert.ok(form.$('div.o_field_widget div.custom-checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        assert.ok(form.$('div.o_field_widget div.custom-checkbox input').prop('disabled'),
            "the checkboxes should be disabled");

        await testUtils.form.clickEdit(form);

        assert.ok(form.$('div.o_field_widget div.custom-checkbox input').prop('disabled'),
            "the checkboxes should be disabled");

        await testUtils.dom.click(form.$('div.o_field_widget div.custom-checkbox > label').eq(1));

        assert.ok(form.$('div.o_field_widget div.custom-checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes: start non empty, then remove twice', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].timmy = [12,14];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<group><field name="timmy" widget="many2many_checkboxes"/></group>' +
                '</form>',
            res_id: 1,
            viewOptions: {mode: 'edit'},
        });

        await testUtils.dom.click(form.$('div.o_field_widget div.custom-checkbox input').eq(0));
        await testUtils.dom.click(form.$('div.o_field_widget div.custom-checkbox input').eq(1));
        await testUtils.form.clickSave(form);
        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').eq(0).prop('checked'),
            "first checkbox should not be checked");
        assert.notOk(form.$('div.o_field_widget div.custom-checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes: values are updated when domain changes', async function (assert) {
        assert.expect(5);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form>
                    <field name="int_field"/>
                    <field name="timmy" widget="many2many_checkboxes" domain="[['id', '>', int_field]]"/>
                </form>`,
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '10');
        assert.containsN(form, '.o_field_widget[name=timmy] .custom-checkbox', 2);
        assert.strictEqual(form.$('.o_field_widget[name=timmy] .o_form_label').text(), 'goldsilver');

        await testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 13);

        assert.containsOnce(form, '.o_field_widget[name=timmy] .custom-checkbox');
        assert.strictEqual(form.$('.o_field_widget[name=timmy] .o_form_label').text(), 'silver');

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes with 40+ values', async function (assert) {
        // 40 is the default limit for x2many fields. However, the many2many_checkboxes is a
        // special field that fetches its data through the fetchSpecialData mechanism, and it
        // uses the name_search server-side limit of 100. This test comes with a fix for a bug
        // that occurred when the user (un)selected a checkbox that wasn't in the 40 first checkboxes,
        // because the piece of data corresponding to that checkbox hadn't been processed by the
        // BasicModel, whereas the code handling the change assumed it had.
        assert.expect(3);

        const records = [];
        for (let id = 1; id <= 90; id++) {
            records.push({
                id,
                display_name: `type ${id}`,
                color: id % 7,
            });
        }
        this.data.partner_type.records = records;
        this.data.partner.records[0].timmy = records.map((r) => r.id);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="timmy" widget="many2many_checkboxes"/></form>',
            res_id: 1,
            async mockRPC(route, args) {
                if (args.method === 'write') {
                    const expectedIds = records.map((r) => r.id);
                    expectedIds.pop();
                    assert.deepEqual(args.args[1].timmy, [[6, false, expectedIds]]);
                }
                return this._super(...arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=timmy] input[type=checkbox]:checked', 90);

        // toggle the last value
        await testUtils.dom.click(form.$('.o_field_widget[name=timmy] input[type=checkbox]:last'));
        assert.notOk(form.$('.o_field_widget[name=timmy] input[type=checkbox]:last').is(':checked'));

        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes with 100+ values', async function (assert) {
        // The many2many_checkboxes widget limits the displayed values to 100 (this is the
        // server-side name_search limit). This test encodes a scenario where there are more than
        // 100 records in the co-model, and all values in the many2many relationship aren't
        // displayed in the widget (due to the limit). If the user (un)selects a checkbox, we don't
        // want to remove all values that aren't displayed from the relation.
        assert.expect(5);

        const records = [];
        for (let id = 1; id < 150; id++) {
            records.push({
                id,
                display_name: `type ${id}`,
                color: id % 7,
            });
        }
        this.data.partner_type.records = records;
        this.data.partner.records[0].timmy = records.map((r) => r.id);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="timmy" widget="many2many_checkboxes"/></form>',
            res_id: 1,
            async mockRPC(route, args) {
                if (args.method === 'write') {
                    const expectedIds = records.map((r) => r.id);
                    expectedIds.shift();
                    assert.deepEqual(args.args[1].timmy, [[6, false, expectedIds]]);
                }
                const result = await this._super(...arguments);
                if (args.method === 'name_search') {
                    assert.strictEqual(result.length, 100,
                        "sanity check: name_search automatically sets the limit to 100");
                }
                return result;
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=timmy] input[type=checkbox]', 100,
            "should only display 100 checkboxes");
        assert.ok(form.$('.o_field_widget[name=timmy] input[type=checkbox]:first').is(':checked'));

        // toggle the first value
        await testUtils.dom.click(form.$('.o_field_widget[name=timmy] input[type=checkbox]:first'));
        assert.notOk(form.$('.o_field_widget[name=timmy] input[type=checkbox]:first').is(':checked'));

        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.module('FieldMany2ManyBinaryMultiFiles');

    QUnit.test('widget many2many_binary', async function (assert) {
        assert.expect(16);
        this.data['ir.attachment'] = {
            fields: {
                name: {string:"Name", type: "char"},
                mimetype: {string: "Mimetype", type: "char"},
            },
            records: [{
                id: 17,
                name: 'Marley&Me.jpg',
                mimetype: 'jpg',
            }],
        };
        this.data.turtle.fields.picture_ids = {
            string: "Pictures",
            type: "many2many",
            relation: 'ir.attachment',
        };
        this.data.turtle.records[0].picture_ids = [17];

        var form = await createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch:'<form string="Turtles">' +
                    '<group><field name="picture_ids" widget="many2many_binary" options="{\'accepted_file_extensions\': \'image/*\'}"/></group>' +
                '</form>',
            archs: {
                'ir.attachment,false,list': '<tree string="Pictures"><field name="name"/></tree>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(route);
                if (route === '/web/dataset/call_kw/ir.attachment/read') {
                    assert.deepEqual(args.args[1], ['name', 'mimetype']);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(form, 'div.o_field_widget.oe_fileupload',
            "there should be the attachment widget");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_attachments').children().length, 1,
            "there should be no attachment");
        assert.containsNone(form, 'div.o_field_widget.oe_fileupload .o_attach',
            "there should not be an Add button (readonly)");
        assert.containsNone(form, 'div.o_field_widget.oe_fileupload .o_attachment .o_attachment_delete',
            "there should not be a Delete button (readonly)");

        // to edit mode
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'div.o_field_widget.oe_fileupload .o_attach',
            "there should be an Add button");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_attach').text().trim(), "Pictures",
            "the button should be correctly named");
        assert.containsOnce(form, 'div.o_field_widget.oe_fileupload .o_hidden_input_file form',
            "there should be a hidden form to upload attachments");

        assert.strictEqual(form.$('input.o_input_file').attr('accept'), 'image/*',
            "there should be an attribute \"accept\" on the input")

        // TODO: add an attachment
        // no idea how to test this

        // delete the attachment
        await testUtils.dom.click(form.$('div.o_field_widget.oe_fileupload .o_attachment .o_attachment_delete'));

        assert.verifySteps([
            '/web/dataset/call_kw/turtle/read',
            '/web/dataset/call_kw/ir.attachment/read',
        ]);

        await testUtils.form.clickSave(form);

        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_attachments').children().length, 0,
            "there should be no attachment");

        assert.verifySteps([
            '/web/dataset/call_kw/turtle/write',
            '/web/dataset/call_kw/turtle/read',
        ]);

        form.destroy();
    });

    QUnit.test('name_create in form dialog', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="bar"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="product_id"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    assert.step('name_create');
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.fields.many2one.searchAndClickItem('product_id',
            {selector: '.modal', search: 'new record'});

        assert.verifySteps(['name_create']);

        form.destroy();
    });

    QUnit.module('FieldReference');

    QUnit.test('Reference field can quick create models', async function (assert) {
        assert.expect(8);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form><field name="reference"/></form>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
                return this._super(...arguments);
            },
        });

        await testUtils.fields.editSelect(form.$('select'), 'partner');
        await testUtils.fields.many2one.searchAndClickItem('reference', {search: 'new partner'});
        await testUtils.form.clickSave(form);

        assert.verifySteps([
            'onchange',
            'name_search', // for the select
            'name_search', // for the spawned many2one
            'name_create',
            'create',
            'read',
            'name_get'
        ], "The name_create method should have been called");

        form.destroy();
    });

    QUnit.test('Reference field in modal readonly mode', async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].trululu = 1;
        this.data.partner.records[1].reference = 'product,41';

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="reference"/>' +
                    '<field name="p"/>' +
                '</form>',
            archs: {
                // make field reference readonly as the modal opens in edit mode
                'partner,false,form': '<form><field name="reference" attrs="{\'readonly\': 1}"/></form>',
                'partner,false,list': '<tree><field name="display_name"/></tree>',
            },
            res_id: 1,
        });

        // Current Form
        assert.equal(form.$('.o_form_uri.o_field_widget[name=reference]').text(), 'xphone',
            'the field reference of the form should have the right value');

        var $cell_o2m = form.$('.o_data_cell');
        assert.equal($cell_o2m.text(), 'second record',
            'the list should have one record');

        await testUtils.dom.click($cell_o2m);

        // In modal
        var $modal = $('.modal-lg');
        assert.equal($modal.length, 1,
            'there should be one modal opened');

        assert.equal($modal.find('.o_form_uri.o_field_widget[name=reference]').text(), 'xpad',
            'The field reference in the modal should have the right value');

        await testUtils.dom.click($modal.find('.o_form_button_cancel'));

        form.destroy();
    });

    QUnit.test('Reference field in modal write mode', async function (assert) {
        assert.expect(5);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].trululu = 1;
        this.data.partner.records[1].reference = 'product,41';

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="reference"/>' +
                    '<field name="p"/>' +
                '</form>',
            archs: {
                'partner,false,form': '<form><field name="reference"/></form>',
                'partner,false,list': '<tree><field name="display_name"/></tree>',
            },
            res_id: 1,
        });

        // current form
        await testUtils.form.clickEdit(form);

        var $fieldRef = form.$('.o_field_widget.o_field_many2one[name=reference]');
        assert.equal($fieldRef.find('option:selected').text(), 'Product',
            'The reference field\'s model should be Product');
        assert.equal($fieldRef.find('.o_input.ui-autocomplete-input').val(), 'xphone',
            'The reference field\'s record should be xphone');

        await testUtils.dom.click(form.$('.o_data_cell'));

        // In modal
        var $modal = $('.modal-lg');
        assert.equal($modal.length, 1,
            'there should be one modal opened');

        var $fieldRefModal = $modal.find('.o_field_widget.o_field_many2one[name=reference]');

        assert.equal($fieldRefModal.find('option:selected').text(), 'Product',
            'The reference field\'s model should be Product');
        assert.equal($fieldRefModal.find('.o_input.ui-autocomplete-input').val(), 'xpad',
            'The reference field\'s record should be xpad');

        form.destroy();
    });

    QUnit.test('reference in form view', async function (assert) {
        assert.expect(15);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="reference" string="custom label"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form': '<form string="Product"><field name="display_name"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action') {
                    assert.deepEqual(args.args[0], [37], "should call get_formview_action with correct id");
                    return Promise.resolve({
                        res_id: 17,
                        type: 'ir.actions.act_window',
                        target: 'current',
                        res_model: 'res.partner'
                    });
                }
                if (args.method === 'get_formview_id') {
                    assert.deepEqual(args.args[0], [37], "should call get_formview_id with correct id");
                    return Promise.resolve(false);
                }
                if (args.method === 'name_search') {
                    assert.strictEqual(args.model, 'partner_type',
                        "the name_search should be done on the newly set model");
                }
                if (args.method === 'write') {
                    assert.strictEqual(args.model, 'partner',
                        "should write on the current model");
                    assert.deepEqual(args.args, [[1], {reference: 'partner_type,12'}],
                        "should write the correct value");
                }
                return this._super(route, args);
            },
        });

        testUtils.mock.intercept(form, 'do_action', function (event) {
            assert.strictEqual(event.data.action.res_id, 17,
                "should do a do_action with correct parameters");
        });

        assert.strictEqual(form.$('a.o_form_uri:contains(xphone)').length, 1,
                        "should contain a link");
        await testUtils.dom.click(form.$('a.o_form_uri'));

        await testUtils.form.clickEdit(form);

        assert.containsN(form, '.o_field_widget', 2,
            "should contain two field widgets (selection and many2one)");
        assert.containsOnce(form, '.o_field_many2one',
            "should contain one many2one");
        assert.strictEqual(form.$('.o_field_widget select').val(), "product",
            "widget should contain one select with the model");
        assert.strictEqual(form.$('.o_field_widget input').val(), "xphone",
            "widget should contain one input with the record");

        var options = _.map(form.$('.o_field_widget select > option'), function (el) {
            return $(el).val();
        });
        assert.deepEqual(options, ['', 'product', 'partner_type', 'partner'],
            "the options should be correctly set");

        await testUtils.dom.click(form.$('.o_external_button'));

        assert.strictEqual($('.modal .modal-title').text().trim(), 'Open: custom label',
                        "dialog title should display the custom string label");
        await testUtils.dom.click($('.modal .o_form_button_cancel'));

        await testUtils.fields.editSelect(form.$('.o_field_widget select'), 'partner_type');
        assert.strictEqual(form.$('.o_field_widget input').val(), "",
            "many2one value should be reset after model change");

        await testUtils.fields.many2one.clickOpenDropdown('reference');
        await testUtils.fields.many2one.clickHighlightedItem('reference');


        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('a.o_form_uri:contains(gold)').length, 1,
                        "should contain a link with the new value");

        form.destroy();
    });

    QUnit.test('interact with reference field changed by onchange', async function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = {
            bar: function (obj) {
                if (!obj.bar) {
                    obj.reference = 'partner,1';
                }
            },
        };
        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form>
                    <field name="bar"/>
                    <field name="reference"/>
                </form>`,
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {
                        bar: false,
                        reference: 'partner,4',
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // trigger the onchange to set a value for the reference field
        await testUtils.dom.click(form.$('.o_field_boolean input'));

        assert.strictEqual(form.$('.o_field_widget[name=reference] select').val(), 'partner');

        // manually update reference field
        await testUtils.fields.many2one.searchAndClickItem('reference', {search: 'aaa'});

        // save
        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.test('default_get and onchange with a reference field', async function (assert) {
        assert.expect(8);

        this.data.partner.fields.reference.default = 'product,37';
        this.data.partner.onchanges = {
            int_field: function (obj) {
                if (obj.int_field) {
                    obj.reference = 'partner_type,' + obj.int_field;
                }
            },
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="int_field"/>' +
                            '<field name="reference"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    assert.step(args.model);
                }
                return this._super(route, args);
            },
        });

        assert.verifySteps(['product'], "the first name_get should have been done");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] select').val(), "product",
            "reference field model should be correctly set");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] input').val(), "xphone",
            "reference field value should be correctly set");

        // trigger onchange
        await testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 12);

        assert.verifySteps(['partner_type'], "the second name_get should have been done");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] select').val(), "partner_type",
            "reference field model should be correctly set");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] input').val(), "gold",
            "reference field value should be correctly set");
        form.destroy();
    });

    QUnit.test('default_get a reference field in a x2m', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.turtles.default = [
            [0, false, {turtle_ref: 'product,37'}]
        ];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="turtles">' +
                            '<tree>' +
                                '<field name="turtle_ref"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            archs: {
                'turtle,false,form': '<form><field name="display_name"/><field name="turtle_ref"/></form>',
            },
        });
        assert.strictEqual(form.$('.o_field_one2many[name="turtles"] .o_data_row:first').text(), "xphone",
            "the default value should be correctly handled");
        form.destroy();
    });

    QUnit.test('widget reference on char field, reset by onchange', async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].foo = 'product,37';
        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = 'product,' + obj.int_field;
            },
        };

        var nbNameGet = 0;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="int_field"/>' +
                            '<field name="foo" widget="reference" readonly="1"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.model === 'product' && args.method === 'name_get') {
                    nbNameGet++;
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(nbNameGet, 1,
            "the first name_get should have been done");
        assert.strictEqual(form.$('a[name="foo"]').text(), "xphone",
            "foo field should be correctly set");

        // trigger onchange
        await testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 41);

        assert.strictEqual(nbNameGet, 2,
            "the second name_get should have been done");
        assert.strictEqual(form.$('a[name="foo"]').text(), "xpad",
            "foo field should have been updated");
        form.destroy();
    });

    QUnit.test('reference and list navigation', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="reference"/></tree>',
        });

        // edit first row
        await testUtils.dom.click(list.$('.o_data_row .o_data_cell').first());
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_field_widget[name="reference"] input')[0], document.activeElement,
            'input of first data row should be selected');

        // press TAB to go to next line
        await testUtils.dom.triggerEvents(list.$('.o_data_row:eq(0) input:eq(1)'),[$.Event('keydown', {
            which: $.ui.keyCode.TAB,
            keyCode: $.ui.keyCode.TAB,
        })]);
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_widget[name="reference"] select')[0], document.activeElement,
            'select of second data row should be selected');

        list.destroy();
    });

    QUnit.test('widget reference with model_field option', async function (assert) {
        assert.expect(5);
        this.data.partner.records[0].reference = false;
        this.data.partner.records[0].model_id = 20;
        this.data.partner.records[1].display_name = "John Smith";
        this.data.product.records[0].display_name = "Product 1";

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form string="Partners">
                        <field name="model_id"/>
                        <field name="reference"  options='{"model_field": "model_id"}'/>
                   </form>`,
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.containsNone(form.$('select'), 'the selection list of the reference field should not exist.');
        assert.strictEqual(form.$('.o_field_many2one[name="reference"] input').val(), '',
            'no record should be selected in the reference field');

        await testUtils.fields.editInput(form.$('.o_field_many2one[name="reference"] input'), 'Product 1');
        await testUtils.dom.click($('.ui-autocomplete .ui-menu-item:first-child'));
        assert.strictEqual(form.$('.o_field_many2one[name="reference"] input').val(), 'Product 1',
            'the Product 1 record should be selected in the reference field');

        await testUtils.fields.editInput(form.$('.o_field_many2one[name="model_id"] input'), 'Partner');
        await testUtils.dom.click($('.ui-autocomplete .ui-menu-item:first-child'));
        assert.strictEqual(form.$('.o_field_many2one[name="reference"] input').val(), '',
            'no record should be selected in the reference field');

        await testUtils.fields.editInput(form.$('.o_field_many2one[name="reference"] input'), 'John');
        await testUtils.dom.click($('.ui-autocomplete .ui-menu-item:first-child'));
        assert.strictEqual(form.$('.o_field_many2one[name="reference"] input').val(), 'John Smith',
            'the John Smith record should be selected in the reference field');

        form.destroy();
    });

    QUnit.test('widget reference with model_field option (model_field not synchronized with reference)', async function (assert) {
        // Checks that the data is not modified even though it is not synchronized.
        // Not synchronized = model_id contains a different model than the one used in reference.
        assert.expect(5);
        this.data.partner.records[0].reference = 'partner,1';
        this.data.partner.records[0].model_id = 20;
        this.data.partner.records[0].display_name = "John Smith";

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form string="Partners">
                        <field name="model_id"/>
                        <field name="reference"  options='{"model_field": "model_id"}'/>
                   </form>`,
            res_id: 1,
        });

        assert.containsNone(form.$('select'), 'the selection list of the reference field should not exist.');
        assert.strictEqual(form.$('.o_field_widget[name="model_id"] span').text(), 'Product',
            'the value of model_id field should be Product');
        assert.strictEqual(form.$('.o_field_widget[name="reference"] span').text(), 'John Smith',
            'the value of model_id field should be John Smith');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_many2one[name="model_id"] input').val(), 'Product',
            'the Product model should be selected in the model_id field');
        assert.strictEqual(form.$('.o_field_many2one[name="reference"] input').val(), 'John Smith',
            'the John Smith record should be selected in the reference field');

        form.destroy();
    });

    QUnit.test('widget reference with model_field option (tree list in form view)', async function (assert) {
        assert.expect(2);

        this.data.turtle.records[0].partner_ids = [1];
        this.data.partner.records[0].reference = 'product,41';
        this.data.partner.records[0].model_id = 20;

        const form = await createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch: `<form string="Turtle">
                        <field name="partner_ids">
                            <tree string="Partner" editable="bottom">
                                <field name="name"/>
                                <field name="model_id"/>
                                <field name="reference" options="{'model_field': 'model_id'}" class="reference_field"/>
                            </tree>
                        </field>
                   </form>`,
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        assert.strictEqual(form.$('.reference_field').text(), 'xpad',
            'should have the second product');

        // Select the second product without changing the model
        await testUtils.dom.click($('.o_list_table .reference_field'));
        await testUtils.dom.click($('.o_list_table .reference_field input'));


        // Enter to select it
        $('.o_list_table .reference_field input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));

        await testUtils.nextTick();

        assert.strictEqual(form.$('.reference_field[name="reference"]').text(), 'xphone',
            'should have selected the first product');

        form.destroy();
    });

    QUnit.test('one2many with extra field from server not in form', async function (assert) {
        assert.expect(6);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="p" >' +
                        '<tree>' +
                            '<field name="datetime"/>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner,false,form': '<form>' +
                                        '<field name="display_name"/>' +
                                    '</form>'},
            mockRPC: function(route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    args.args[1].p[0][2].datetime = '2018-04-05 12:00:00';
                }
                return this._super.apply(this, arguments);
            }
        });

        await testUtils.form.clickEdit(form);

        var x2mList = form.$('.o_field_x2many_list[name=p]');

        // Add a record in the list
        await testUtils.dom.click(x2mList.find('.o_field_x2many_list_row_add a'));

        var modal = $('.modal-lg');

        var nameInput = modal.find('input.o_input[name=display_name]');
        await testUtils.fields.editInput(nameInput, 'michelangelo');

        // Save the record in the modal (though it is still virtual)
        await testUtils.dom.click(modal.find('.btn-primary').first());

        assert.equal(x2mList.find('.o_data_row').length, 1,
            'There should be 1 records in the x2m list');

        var newlyAdded = x2mList.find('.o_data_row').eq(0);

        assert.equal(newlyAdded.find('.o_data_cell').first().text(), '',
            'The create_date field should be empty');
        assert.equal(newlyAdded.find('.o_data_cell').eq(1).text(), 'michelangelo',
            'The display name field should have the right value');

        // Save the whole thing
        await testUtils.form.clickSave(form);

        x2mList = form.$('.o_field_x2many_list[name=p]');

        // Redo asserts in RO mode after saving
        assert.equal(x2mList.find('.o_data_row').length, 1,
            'There should be 1 records in the x2m list');

        newlyAdded = x2mList.find('.o_data_row').eq(0);

        assert.equal(newlyAdded.find('.o_data_cell').first().text(), '04/05/2018 12:00:00',
            'The create_date field should have the right value');
        assert.equal(newlyAdded.find('.o_data_cell').eq(1).text(), 'michelangelo',
            'The display name field should have the right value');

        form.destroy();
    });

    QUnit.test('one2many invisible depends on parent field', async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="Partner page">' +
                                '<field name="bar"/>' +
                                '<field name="p">' +
                                    '<tree>' +
                                        '<field name="foo" attrs="{\'column_invisible\': [(\'parent.product_id\', \'!=\', False)]}"/>' +
                                        '<field name="bar" attrs="{\'column_invisible\': [(\'parent.bar\', \'=\', False)]}"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        assert.containsN(form, 'th:not(.o_list_record_remove_header)', 2,
            "should be 2 columns in the one2many");
        await testUtils.form.clickEdit(form);
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(form, 'th:not(.o_list_record_remove_header)',
            "should be 1 column when the product_id is set");
        await testUtils.fields.editAndTrigger(form.$('.o_field_many2one[name="product_id"] input'),
            '', 'keyup');
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(form, 'th:not(.o_list_record_remove_header)', 2,
            "should be 2 columns in the one2many when product_id is not set");
        await testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(form, 'th:not(.o_list_record_remove_header)',
            "should be 1 column after the value change");
        form.destroy();
    });

    QUnit.test('one2many column visiblity depends on onchange of parent field', async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[0].bar = false;

        this.data.partner.onchanges.p = function (obj) {
            // set bar to true when line is added
            if (obj.p.length > 1 && obj.p[1][2].foo === 'New line') {
                obj.bar = true;
            }
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="bar"/>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="foo"/>' +
                            '<field name="int_field" attrs="{\'column_invisible\': [(\'parent.bar\', \'=\', False)]}"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        // bar is false so there should be 1 column
        assert.containsOnce(form, 'th:not(.o_list_record_remove_header)',
            "should be only 1 column ('foo') in the one2many");
        assert.containsOnce(form, '.o_list_view .o_data_row', "should contain one row");

        await testUtils.form.clickEdit(form);

        // add a new o2m record
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        form.$('.o_field_one2many input:first').focus();
        await testUtils.fields.editInput(form.$('.o_field_one2many input:first'), 'New line');
        await testUtils.dom.click(form.$el);

        assert.containsN(form, 'th:not(.o_list_record_remove_header)', 2,
            "should be 2 columns('foo' + 'int_field')");

        form.destroy();
    });

    QUnit.test('one2many column_invisible on view not inline', async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="Partner page">' +
                                '<field name="bar"/>' +
                                '<field name="p"/>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner,false,list': '<tree>' +
                    '<field name="foo" attrs="{\'column_invisible\': [(\'parent.product_id\', \'!=\', False)]}"/>' +
                    '<field name="bar" attrs="{\'column_invisible\': [(\'parent.bar\', \'=\', False)]}"/>' +
                '</tree>',
            },
        });
        assert.containsN(form, 'th:not(.o_list_record_remove_header)', 2,
            "should be 2 columns in the one2many");
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_field_many2one[name="product_id"] input'));
        await testUtils.fields.many2one.clickHighlightedItem("product_id");
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(form, 'th:not(.o_list_record_remove_header)',
            "should be 1 column when the product_id is set");
        await testUtils.fields.editAndTrigger(form.$('.o_field_many2one[name="product_id"] input'),
            '', 'keyup');
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(form, 'th:not(.o_list_record_remove_header)', 2,
            "should be 2 columns in the one2many when product_id is not set");
        await testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(form, 'th:not(.o_list_record_remove_header)',
            "should be 1 column after the value change");
        form.destroy();
    });

    QUnit.test('one2many field in edit mode with optional fields and trash icon', async function (assert) {
        assert.expect(13);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        this.data.partner.records[0].p = [2];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="p"/>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner,false,list': '<tree editable="top">' +
                    '<field name="foo" optional="show"/>' +
                    '<field name="bar" optional="hide"/>' +
                '</tree>',
            },
            services: {
                local_storage: RamStorageService,
            },
        });

        // should have 2 columns 1 for foo and 1 for advanced dropdown
        assert.containsN(form.$('.o_field_one2many'), 'th:not(.o_list_record_remove_header)', 1,
            "should be 1 th in the one2many in readonly mode");
        assert.containsOnce(form.$('.o_field_one2many table'), '.o_optional_columns_dropdown_toggle',
            "should have the optional columns dropdown toggle inside the table");
        await testUtils.form.clickEdit(form);
        // should have 2 columns 1 for foo and 1 for trash icon, dropdown is displayed
        // on trash icon cell, no separate cell created for trash icon and advanced field dropdown
        assert.containsN(form.$('.o_field_one2many'), 'th', 2,
            "should be 2 th in the one2many edit mode");
        assert.containsN(form.$('.o_field_one2many'), '.o_data_row:first > td', 2,
            "should be 2 cells in the one2many in edit mode");

        await testUtils.dom.click(form.$('.o_field_one2many table .o_optional_columns_dropdown_toggle'));
        assert.containsN(form.$('.o_field_one2many'), 'div.o_optional_columns div.dropdown-item:visible', 2,
            "dropdown have 2 advanced field foo with checked and bar with unchecked");
        await testUtils.dom.click(form.$('div.o_optional_columns div.dropdown-item:eq(1) input'));
        assert.containsN(form.$('.o_field_one2many'), 'th', 3,
            "should be 3 th in the one2many after enabling bar column from advanced dropdown");

        await testUtils.dom.click(form.$('div.o_optional_columns div.dropdown-item:first input'));
        assert.containsN(form.$('.o_field_one2many'), 'th', 2,
            "should be 2 th in the one2many after disabling foo column from advanced dropdown");

        assert.containsN(form.$('.o_field_one2many'), 'div.o_optional_columns div.dropdown-item:visible', 2,
            "dropdown is still open");
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        // use of owlCompatibilityExtraNextTick because the x2many field is reset, meaning that
        // 1) its list renderer is updated (updateState is called): this is async and as it
        // contains a FieldBoolean, which is written in Owl, it completes in the nextAnimationFrame
        // 2) when this is done, the control panel is updated: as it is written in owl, this is
        // done in the nextAnimationFrame
        // -> we need to wait for 2 nextAnimationFrame to ensure that everything is fine
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(form.$('.o_field_one2many'), 'div.o_optional_columns div.dropdown-item:visible', 0,
            "dropdown is closed");
        var $selectedRow = form.$('.o_field_one2many tr.o_selected_row');
        assert.strictEqual($selectedRow.length, 1, "should have selected row i.e. edition mode");

        await testUtils.dom.click(form.$('.o_field_one2many table .o_optional_columns_dropdown_toggle'));
        await testUtils.dom.click(form.$('div.o_optional_columns div.dropdown-item:first input'));
        $selectedRow = form.$('.o_field_one2many tr.o_selected_row');
        assert.strictEqual($selectedRow.length, 0,
            "current edition mode discarded when selecting advanced field");
        assert.containsN(form.$('.o_field_one2many'), 'th', 3,
            "should be 3 th in the one2many after re-enabling foo column from advanced dropdown");

        // check after form reload advanced column hidden or shown are still preserved
        await form.reload();
        assert.containsN(form.$('.o_field_one2many .o_list_view'), 'th', 3,
            "should still have 3 th in the one2many after reloading whole form view");

        form.destroy();
    });

    QUnit.module('TabNavigation');
    QUnit.test('when Navigating to a many2one with tabs, it receives the focus and adds a new line', async function (assert) {
         assert.expect(3);

        var form = await createView({
            View: FormView,
            model: 'partner',
            viewOptions: {
                mode: 'edit',
            },
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="Partner page">' +
                                '<field name="turtles">' +
                                    '<tree editable="bottom">' +
                                        '<field name="turtle_foo"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$el.find('input[name="qux"]')[0],
                            document.activeElement,
                            "initially, the focus should be on the 'qux' field because it is the first input");
        await testUtils.fields.triggerKeydown(form.$el.find('input[name="qux"]'), 'tab');
        assert.strictEqual(assert.strictEqual(form.$el.find('input[name="turtle_foo"]')[0],
                            document.activeElement,
                            "after tab, the focus should be on the many2one on the first input of the newly added line"));

        form.destroy();
    });

    QUnit.test('when Navigating to a many to one with tabs, it places the focus on the first visible field', async function (assert) {
        assert.expect(3);

       var form = await createView({
           View: FormView,
           model: 'partner',
           viewOptions: {
               mode: 'edit',
           },
           data: this.data,
           arch:'<form string="Partners">' +
                   '<sheet>' +
                       '<group>' +
                           '<field name="qux"/>' +
                       '</group>' +
                       '<notebook>' +
                           '<page string="Partner page">' +
                               '<field name="turtles">' +
                                   '<tree editable="bottom">' +
                                       '<field name="turtle_bar" invisible="1"/>'+
                                       '<field name="turtle_foo"/>' +
                                   '</tree>' +
                               '</field>' +
                           '</page>' +
                       '</notebook>' +
                   '</sheet>' +
               '</form>',
           res_id: 1,
       });

       assert.strictEqual(form.$el.find('input[name="qux"]')[0],
                           document.activeElement,
                           "initially, the focus should be on the 'qux' field because it is the first input");
       form.$el.find('input[name="qux"]').trigger($.Event('keydown', {
           which: $.ui.keyCode.TAB,
           keyCode: $.ui.keyCode.TAB,
       }));
       await testUtils.owlCompatibilityExtraNextTick();
       await testUtils.dom.click(document.activeElement);
       assert.strictEqual(assert.strictEqual(form.$el.find('input[name="turtle_foo"]')[0],
                           document.activeElement,
                           "after tab, the focus should be on the many2one"));

       form.destroy();
    });

    QUnit.test('when Navigating to a many2one with tabs, not filling any field and hitting tab,' +
            ' we should not add a first line but navigate to the next control', async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].turtles = [];

        var form = await createView({
            View: FormView,
            model: 'partner',
            viewOptions: {
                mode: 'edit',
            },
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="Partner page">' +
                                '<field name="turtles">' +
                                    '<tree editable="bottom">' +
                                        '<field name="turtle_foo"/>' +
                                        '<field name="turtle_description"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$el.find('input[name="qux"]')[0],
            document.activeElement,
            "initially, the focus should be on the 'qux' field because it is the first input");
        await testUtils.fields.triggerKeydown(form.$el.find('input[name="qux"]'), 'tab');

        // skips the first field of the one2many
        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        // skips the second (and last) field of the one2many
        await testUtils.fields.triggerKeydown($(document.activeElement), 'tab');
        assert.strictEqual(assert.strictEqual(form.$el.find('input[name="foo"]')[0],
            document.activeElement,
            "after tab, the focus should be on the many2one"));

        form.destroy();
    });

    QUnit.test('when Navigating to a many to one with tabs, editing in a popup, the popup should receive the focus then give it back', async function (assert) {
        assert.expect(3);

        await makeLegacyDialogMappingTestEnv();

        this.data.partner.records[0].turtles = [];

        var form = await createView({
            View: FormView,
            model: 'partner',
            viewOptions: {
                mode: 'edit',
            },
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="Partner page">' +
                                '<field name="turtles">' +
                                    '<tree>' +
                                        '<field name="turtle_foo"/>' +
                                        '<field name="turtle_description"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</page>' +
                        '</notebook>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            archs: {
                'turtle,false,form': '<form><group><field name="turtle_foo"/><field name="turtle_int"/></group></form>',
            },
        });

        assert.strictEqual(form.$el.find('input[name="qux"]')[0],
            document.activeElement,
            "initially, the focus should be on the 'qux' field because it is the first input");
        await testUtils.fields.triggerKeydown(form.$el.find('input[name="qux"]'), 'tab');
        assert.strictEqual($.find('input[name="turtle_foo"]')[0],
            document.activeElement,
            "when the one2many received the focus, the popup should open because it automatically adds a new line");

        await testUtils.fields.triggerKeydown($('input[name="turtle_foo"]'), 'escape');
        assert.strictEqual(form.$el.find('.o_field_x2many_list_row_add a')[0],
            document.activeElement,
            "after escape, the focus should be back on the add new line link");

       form.destroy();
    });

    QUnit.test('when creating a new many2one on a x2many then discarding it immediately with ESCAPE, it should not crash', async function (assert) {
        assert.expect(1);

        this.data.partner.records[0].turtles = [];

        var form = await createView({
            View: FormView,
            model: 'partner',
            viewOptions: {
                mode: 'edit',
            },
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="turtles">' +
                            '<tree editable="top">' +
                                '<field name="turtle_foo"/>' +
                                '<field name="turtle_trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner,false,form': '<form><group><field name="foo"/><field name="bar"/></group></form>'
            },
        });

        // add a new line
        await testUtils.dom.click(form.$el.find('.o_field_x2many_list_row_add>a'));

        // open the field turtle_trululu (one2many)
        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;
        await testUtils.dom.click(form.$el.find('.o_input_dropdown>input'));

        await testUtils.fields.editInput(form.$('.o_field_many2one input'), 'ABC');
        // click create and edit
        testUtils.dom.click($('.ui-autocomplete .ui-menu-item a:contains(Create and)').trigger('mouseenter'));

        // hit escape immediately
        var escapeKey = $.ui.keyCode.ESCAPE;
        $(document.activeElement).trigger(
            $.Event('keydown', {which: escapeKey, keyCode: escapeKey}));

        assert.containsNone(document.body, ".modal");
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        form.destroy();
    });

    QUnit.test('navigating through an editable list with custom controls [REQUIRE FOCUS]', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<control>' +
                                '<create string="Custom 1" context="{\'default_foo\': \'1\'}"/>' +
                                '<create string="Custom 2" context="{\'default_foo\': \'2\'}"/>' +
                            '</control>' +
                            '<field name="foo"/>' +
                        '</tree>' +
                    '</field>' +
                    '<field name="int_field"/>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(document.activeElement, form.$('.o_field_widget[name="display_name"]')[0],
            "first input should be focused by default");

        // press tab to navigate to the list
        await testUtils.fields.triggerKeydown(
            form.$('.o_field_widget[name="display_name"]'), 'tab');
        // press ESC to cancel 1st control click (create)
        await testUtils.fields.triggerKeydown(
            form.$('.o_data_cell input'), 'escape');
        assert.strictEqual(document.activeElement, form.$('.o_field_x2many_list_row_add a:first')[0],
            "first editable list control should now have the focus");

        // press right to focus the second control
        await testUtils.fields.triggerKeydown(
            form.$('.o_field_x2many_list_row_add a:first'), 'right');
        assert.strictEqual(document.activeElement, form.$('.o_field_x2many_list_row_add a:nth(1)')[0],
            "second editable list control should now have the focus");

        // press left to come back to first control
        await testUtils.fields.triggerKeydown(
            form.$('.o_field_x2many_list_row_add a:nth(1)'), 'left');
        assert.strictEqual(document.activeElement, form.$('.o_field_x2many_list_row_add a:first')[0],
            "first editable list control should now have the focus");

        // press tab to leave the list
        await testUtils.fields.triggerKeydown(
            form.$('.o_field_x2many_list_row_add a:first'), 'tab');
        assert.strictEqual(document.activeElement, form.$('.o_field_widget[name="int_field"]')[0],
            "last input should now be focused");

        form.destroy();
    });
    QUnit.test('Check onchange with two consecutive many2one', async function (assert) {
        assert.expect(2);
        this.data.product.fields.product_partner_ids = { string: "User", type: 'one2many', relation: 'partner' };
        this.data.product.records[0].product_partner_ids = [1];
        this.data.product.records[1].product_partner_ids = [2];
        this.data.turtle.fields.product_ids = { string: "Product", type: "one2many", relation: 'product' };
        this.data.turtle.fields.user_ids = { string: "Product", type: "one2many", relation: 'user' };
        this.data.turtle.onchanges = {
            turtle_trululu: function (record) {
                record.product_ids = [37];
                record.user_ids = [17, 19];
            },
        };
        var form = await createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch: 
                '<form string="Turtles">' +
                    '<field string="Product" name="turtle_trululu"/>' +
                    '<field readonly="1" string="Related field" name="product_ids">' +
                        '<tree>' +
                            '<field widget="many2many_tags" name="product_partner_ids"/>' +
                        '</tree>' +
                    '</field>' +
                    '<field readonly="1" string="Second related field" name="user_ids">' +
                        '<tree>' +
                            '<field widget="many2many_tags" name="partner_ids"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        await testUtils.fields.many2one.clickOpenDropdown("turtle_trululu");
        await testUtils.fields.many2one.searchAndClickItem('turtle_trululu', {search: 'first record'});

        const getElementTextContent = name => [...document.querySelectorAll(`.o_field_many2manytags[name="${name}"] .badge.o_tag_color_0 > span`)]
            .map(x=>x.textContent);
        assert.deepEqual(
            getElementTextContent('product_partner_ids'),
            ['first record'],
            "should have the correct value in the many2many tag widget");
        assert.deepEqual(
            getElementTextContent('partner_ids'),
            ['first record', 'second record'],
            "should have the correct values in the many2many tag widget");
        form.destroy();
    });
});
});
});
