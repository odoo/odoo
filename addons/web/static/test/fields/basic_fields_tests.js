odoo.define('web.basic_fields_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('basic_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    date: {string: "A date", type: "date", searchable: true},
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true},
                    bar: {string: "Bar", type: "boolean", default: true, searchable: true},
                    int_field: {string: "int_field", type: "integer", sortable: true, searchable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1], searchable: true},
                    p: {string: "one2many field", type: "one2many", relation: 'partner', searchable: true},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner', searchable: true},
                    timmy: {string: "pokemon", type: "many2many", relation: 'partner_type', searchable: true},
                    product_id: {string: "Product", type: "many2one", relation: 'product', searchable: true},
                    sequence: {type: "integer", string: "Sequence", searchable: true},
                },
                records: [{
                    id: 1,
                    date: "2017-02-03",
                    display_name: "first record",
                    bar: true,
                    foo: "yop",
                    int_field: 10,
                    qux: 0.44,
                    p: [],
                    timmy: [],
                    trululu: 4,
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
                    sequence: 4
                }, {
                    id: 4,
                    display_name: "aaa",
                    foo: "abc",
                    sequence: 9,
                },
                {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3, m2o: 1, m2m: []},
                {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9, m2o: 1, m2m: [1]}],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char", searchable: true}
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
                    name: {string: "Partner Type", type: "char", searchable: true},
                    color: {string: "Color index", type: "integer", searchable: true},
                },
                records: [
                    {id: 12, display_name: "gold", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                ]
            },
        };
    }
}, function () {

    QUnit.module('FieldBoolean');

    QUnit.test('boolean field rendering in list view', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="bar"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input:checked').length, 4,
            "should have 4 checked input");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input').length, 5,
            "should have 5 checkboxes");
    });

    QUnit.module('FieldFloat');

    QUnit.test('float field rendering in list view', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="qux"/></tree>',
        });

        assert.strictEqual(list.$('.o_list_number').length, 5, "should have 5 cells with .o_list_number");
    });

    QUnit.test('float fields use correct digit precision', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('span.o_form_field_number:contains(0.4)').length, 1,
                            "should contain a number rounded to 1 decimal");
    });

    QUnit.module('EmailWidget');


    QUnit.test('email widget works correctly', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="email"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').length, 1,
                        "should have a anchor with correct classes");
    });

    QUnit.module('FieldChar');


    QUnit.test('widget isValid method works', function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.required = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        var charField = form.renderer.widgets[0];
        assert.strictEqual(charField.isValid(), true);
    });

    QUnit.test('char fields in edit mode', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').length, 1,
                    "should have an input for the char field foo");
    });

    QUnit.module('UrlWidget');

    QUnit.test('url widget works correctly', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="url"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').length, 1,
                        "should have a anchor with correct classes");
    });

    QUnit.module('FieldText');

    QUnit.test('text fields are correctly rendered', function (assert) {
        assert.expect(7);

        this.data.partner.fields.foo.type = 'text';
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('div.o_form_textarea').length, "should have a text area");
        assert.strictEqual(form.$('div.o_form_textarea').text(), 'yop', 'should be "yop" in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        var $textarea = form.$('.o_form_textarea textarea');
        assert.ok($textarea.length, "should have a text area");
        assert.strictEqual($textarea.val(), 'yop', 'should still be "yop" in edit');

        $textarea.val('hello').trigger('input');
        assert.strictEqual($textarea.val(), 'hello', 'should be "hello" after first edition');

        $textarea.val('hello world').trigger('input');
        assert.strictEqual($textarea.val(), 'hello world', 'should be "hello world" after second edition');

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('div.o_form_textarea').text(), 'hello world',
            'should be "hello world" after save');
    });

    QUnit.test('text fields in edit mode have correct height', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.type = 'text';
        this.data.partner.records[0].foo = "f\nu\nc\nk\nm\ni\nl\ng\nr\no\nm";
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        var $field = form.$('div.o_list_text');

        assert.strictEqual($field.outerHeight(), $field[0].scrollHeight,
            "text field should not have a scroll bar");

        form.$buttons.find('.o_form_button_edit').click();

        var $textarea = form.$('textarea:first');

        // the difference is to take small calculation errors into account
        assert.strictEqual($textarea.innerHeight(), $textarea[0].scrollHeight,
            "textarea should not have a scroll bar");
    });


    QUnit.test('text field rendering in list view', function (assert) {
        assert.expect(1);

        var data = {
            foo: {
                fields: {foo: {string: "F", type: "text"}},
                records: [{id: 1, foo: "some text"}]
            },
        };
        var list = createView({
            View: ListView,
            model: 'foo',
            data: data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('tbody td.o_list_text:contains(some text)').length, 1,
            "should have a td with the .o_list_text class");
    });

    QUnit.test('field text in editable list view', function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.type = 'text';

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        assert.ok(list.$('textarea').first().is(':focus'),
            "text area should have the focus (make sure the test window had the focus)");
    });


    QUnit.module('JournalDashboardGraph');

    QUnit.test('graph dashboard widget is rendered correctly', function (assert) {
        assert.expect(2);

        _.extend(this.data.partner.fields, {
            graph_data: { string: "Graph Data", type: "text" },
            graph_type: {
                string: "Graph Type",
                type: "selection",
                selection: [['line', 'Line'], ['bar', 'Bar']]
            },
        });
        this.data.partner.records[0].graph_type = "bar";
        this.data.partner.records[1].graph_type = "line";
        var graph_values = [
            {'value': 300, 'label': '5-11 Dec'},
            {'value': 500, 'label': '12-18 Dec'},
            {'value': 100, 'label': '19-25 Dec'},
        ];
        this.data.partner.records[0].graph_data = JSON.stringify([{
            color: 'red',
            title: 'Partner 0',
            values: graph_values,
            key: 'A key',
            area: true,
        }]);
        this.data.partner.records[1].graph_data = JSON.stringify([{
            color: 'blue',
            title: 'Partner 1',
            values: graph_values,
            key: 'A key',
            area: true,
        }]);
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                        '</div>' +
                    '</t>' +
                '</templates></kanban>',
            domain: [['id', 'in', [1, 2]]],
            manualDestroy: true,
        });

        // nvd3 seems to do a setTimeout(0) each time the addGraph function is
        // called, which is done twice in this case as there are 2 records.
        // for that reason, we need to do two setTimeout(0) as well here to ensure
        // that both graphs are rendered before starting to check if the rendering
        // is correct.
        var done = assert.async();
        return concurrency.delay(0).then(function () {
            return concurrency.delay(0);
        }).then(function () {
            assert.ok(kanban.$('.o_kanban_record:first() .o_graph_barchart').length,
                "graph of first record should be a barchart");
            assert.ok(kanban.$('.o_kanban_record:nth(1) .o_graph_linechart').length,
                "graph of second record should be a linechart");
            kanban.destroy();
            done();
        });

    });

    QUnit.module('AceEditor');

    QUnit.test('ace widget on text fields works', function (assert) {
        assert.expect(3);
        var done = assert.async();

        assert.notOk('ace' in window, "the ace library should not be loaded");
        this.data.partner.fields.foo.type = 'text';
        testUtils.createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" widget="ace"/>' +
                '</form>',
            res_id: 1,
        }).then(function (form) {
            assert.ok('ace' in window, "the ace library should now be loaded");
            assert.ok(form.$('div.ace_content').length, "should have rendered something with ace editor");
            delete window.require;
            delete window.ace;
            done();
        });
    });

    QUnit.module('HandleWidget');

    QUnit.test('handle widget', function (assert) {
        assert.expect(7);

        this.data.partner.records[0].p = [2, 4];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="sequence" widget="handle"/>' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('td span.o_row_handle').text(), "",
            "handle should not have any content");

        assert.notOk(form.$('td span.o_row_handle').is(':visible'),
            "handle should be invisible in readonly mode");

        assert.strictEqual(form.$('span.o_row_handle').length, 2, "should have 2 handles");

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('td:first').hasClass('o_readonly'),
            "column should be displayed as readonly");

        assert.ok(form.$('td:first').hasClass('o_handle_cell'),
            "column widget should be displayed in css class");

        assert.ok(form.$('td span.o_row_handle').is(':visible'),
            "handle should be visible in readonly mode");

        form.$('td').eq(1).click();
        assert.strictEqual(form.$('td:first span.o_row_handle').length, 1,
            "content of the cell should have been replaced");
    });

    QUnit.module('FieldDate');

    QUnit.test('date field in edit mode', function (assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    assert.strictEqual(args.args[1].date, '2017-02-22', 'the correct value should be saved');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_form_field_date').text(), '02/03/2017',
            'the date should be correctly displayed in readonly');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        // click on the input and select another value
        form.$('.o_datepicker_input').click();
        assert.ok(form.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        form.$('.day:contains(22)').click(); // select the 22 February
        assert.ok(!form.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/22/2017',
            'the selected date should be displayed in the input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_date').text(), '02/22/2017',
            'the selected date should be displayed after saving');
    });

    QUnit.test('field date in editable list view', function (assert) {
        assert.expect(1);

        this.data.partner.fields.date.default = "2017-02-10";
        this.data.partner.records = [];

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        assert.ok(list.$('input').is(':focus'),
            "date input should have the focus (make sure the test window had the focus)");
    });

    QUnit.module('FieldDomain');

    QUnit.test('basic domain field usage is ok', function (assert) {
        assert.expect(6);

        this.data.partner.records[0].foo = "[]";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="domain" options="{\'model\': \'partner_type\'}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();

        // As the domain is empty, there should be a button to add the first
        // domain part
        var $domain = form.$(".o_form_field_domain");
        var $domainAddFirstNodeButton = $domain.find(".o_domain_add_first_node_button");
        assert.equal($domainAddFirstNodeButton.length, 1,
            "there should be a button to create first domain element");

        // Clicking on the button should add the [["id", "=", "1"]] domain, so
        // there should be a field selector in the DOM
        $domainAddFirstNodeButton.click();
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing the field selector input should open the field selector
        // popover
        $fieldSelector.find("> input").focus();
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        // The popover should contain the list of partner_type fields and so
        // there should be the "Color index" field
        var $lis = $fieldSelectorPopover.find("li");
        var $colorIndex = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Color index") >= 0) {
                $colorIndex = $li;
            }
        });
        assert.equal($colorIndex.length, 1,
            "field selector popover should contain 'Color index' field");

        // Clicking on this field should close the popover, then changing the
        // associated value should reveal one matched record
        $colorIndex.click();
        $domain.find(".o_domain_leaf_value_input").val(2).change();
        assert.equal($domain.find(".o_domain_show_selection_button").text().trim().substr(0, 2), "1 ",
            "changing color value to 2 should reveal only one record");

        // Saving the form view should show a readonly domain containing the
        // "color" field
        form.$buttons.find('.o_form_button_save').click();
        $domain = form.$(".o_form_field_domain");
        assert.ok($domain.html().indexOf("color") >= 0,
            "field selector readonly value should now contain 'color'");
    });

    QUnit.test('domain field is correctly reset on every view change', function (assert) {
        assert.expect(7);

        this.data.partner.records[0].foo = '[["id","=",1]]';
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="bar"/>' +
                            '<field name="foo" widget="domain" options="{\'model\': \'bar\'}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();

        // As the domain is equal to [["id", "=", 1]] there should be a field
        // selector to change this
        var $domain = form.$(".o_form_field_domain");
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing its input should open the field selector popover
        $fieldSelector.find("> input").focus();
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        // As the value of the "bar" field is "product", the field selector
        // popover should contain the list of "product" fields
        var $lis = $fieldSelectorPopover.find("li");
        var $sampleLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Product Name") >= 0) {
                $sampleLi = $li;
            }
        });
        assert.strictEqual($lis.length, 1,
            "field selector popover should contain only one field");
        assert.strictEqual($sampleLi.length, 1,
            "field selector popover should contain 'Product Name' field");

        // Now change the value of the "bar" field to "partner_type"
        form.$(".o_field_widget.o_form_input").click().val("partner_type").trigger("input");

        // Refocusing the field selector input should open the popover again
        $fieldSelector = form.$(".o_field_selector");
        $fieldSelector.find("> input").focus();
        $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        // Now the list of fields should be the ones of the "partner_type" model
        $lis = $fieldSelectorPopover.find("li");
        $sampleLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Color index") >= 0) {
                $sampleLi = $li;
            }
        });
        assert.strictEqual($lis.length, 2,
            "field selector popover should contain two fields");
        assert.strictEqual($sampleLi.length, 1,
            "field selector popover should contain 'Color index' field");
    });
});
});
});
