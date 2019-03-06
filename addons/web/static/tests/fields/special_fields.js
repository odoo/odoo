odoo.define('web.special_fields_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('special_fields', {
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
                    turtles: {string: "one2many turtle field", type: "one2many", relation: 'turtle'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    color: {
                        type: "selection",
                        selection: [['red', "Red"], ['black', "Black"]],
                        default: 'red',
                    },
                    date: {string: "Some Date", type: "date"},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                    user_id: {string: "User", type: 'many2one', relation: 'user'},
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
                    turtle_foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    turtle_bar: {string: "Bar", type: "boolean", default: true},
                    turtle_int: {string: "int", type: "integer", sortable: true},
                    turtle_qux: {string: "Qux", type: "float", digits: [16,1], required: true, default: 1.5},
                    turtle_description: {string: "Description", type: "text"},
                    turtle_trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
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
                    turtle_bar: false,
                    turtle_foo: "kawa",
                    turtle_int: 21,
                    turtle_qux: 9.8,
                    partner_ids: [],
                }],
            },
            user: {
                fields: {
                    name: {string: "Name", type: "char"}
                },
                records: [{
                    id: 17,
                    name: "Aline",
                }, {
                    id: 19,
                    name: "Christine",
                }]
            },
        };
    }
}, function () {

    QUnit.module('FieldTimezoneMismatch');

    QUnit.test('widget timezone_mismatch in a list view', function (assert) {
        assert.expect(5);

        this.data.partner.fields.tz_offset = {
            string: "tz_offset",
            type: "char"
        };
        this.data.partner.records.forEach(function (r) {
            r.color = 'red';
            r.tz_offset = 0;
        });
        this.data.partner.onchanges = {
            color: function (r) {
                r.tz_offset = '+4800'; // make sur we have a mismatch
            }
        };

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Colors" editable="top">' +
                        '<field name="tz_offset" invisible="True"/>' +
                        '<field name="color" widget="timezone_mismatch"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('td:contains(Red)').length, 3,
            "should have 3 rows with correct value");
        list.$('td:contains(Red):first').click();

        var $td = list.$('tbody tr.o_selected_row td:not(.o_list_record_selector)');

        assert.strictEqual($td.find('select').length, 1, "td should have a child 'select'");
        assert.strictEqual($td.contents().length, 1, "select tag should be only child of td");

        $td.find('select').val('"black"').trigger('change');

        assert.strictEqual($td.find('.o_tz_warning').length, 1, "Should display icon alert");
        assert.ok($td.find('select option:selected').text().match(/Black\s+\([0-9]+\/[0-9]+\/[0-9]+ [0-9]+:[0-9]+:[0-9]+\)/), "Should display the datetime in the selected timezone");
        list.destroy();
    });

    QUnit.test('widget timezone_mismatch in a form view', function (assert) {
        assert.expect(1);

        this.data.partner.fields.tz_offset = {
            string: "tz_offset",
            type: "char"
        };
        this.data.partner.fields.tz = {
            type: "selection",
            selection: [['Europe/Brussels', "Europe/Brussels"], ['America/Los_Angeles', "America/Los_Angeles"]],
        };
        this.data.partner.records[0].tz = false;
        this.data.partner.records[0].tz_offset = '+4800';

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<field name="tz_offset" invisible="True"/>' +
                    '<field name="tz" widget="timezone_mismatch"/>' +
                '</form>',
        });
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('select').length, 1, "should have the select field");
        form.destroy();
    });

    QUnit.test('widget timezone_mismatch in a form view edit mode with mismatch', function (assert) {
        assert.expect(3);

        this.data.partner.fields.tz_offset = {
            string: "tz_offset",
            type: "char"
        };
        this.data.partner.fields.tz = {
            type: "selection",
            selection: [['Europe/Brussels', "Europe/Brussels"], ['America/Los_Angeles', "America/Los_Angeles"]],
        };
        this.data.partner.records[0].tz = 'America/Los_Angeles';
        this.data.partner.records[0].tz_offset = '+4800';

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<field name="tz_offset" invisible="True"/>' +
                    '<field name="tz" widget="timezone_mismatch" options="{\'tz_offset_field\': \'tz_offset\'}"/>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
        });

        var $timezoneEl = form.$('select[name="tz"]');
        assert.strictEqual($timezoneEl.children().length, 3,
            'The select element should have 3 children');

        var $timezoneMismatch = form.$('.o_tz_warning');
        assert.strictEqual($timezoneMismatch.length, 1,
            'timezone mismatch is present');

        assert.notOk($timezoneMismatch.children().length,
            'The mismatch element should not have children');
        form.destroy();
    });

    QUnit.module('FieldReportLayout');

    QUnit.test('report_layout widget in form view', function (assert) {
        assert.expect(3);

        this.data['report.layout'] = {
            fields: {
                view_id: {string: "Document Template", type: "many2one", relation: "product"},
                image: {string: "Preview image src", type: "char"},
                pdf: {string: "Preview pdf src", type: "char"}
            },
            records: [{
                id: 1,
                view_id: 37,
                image: "/web/static/toto.png",
                pdf: "/web/static/toto.pdf",
            }, {
                id: 2,
                view_id: 41,
                image: "/web/static/tata.png",
                pdf: "/web/static/tata.pdf",
            }]
        };
        this.data.partner.records[1].product_id = false;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="product_id" widget="report_layout"/> '+
                  '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.img.img-fluid').length, 2,
            "Two images should be rendered");
        assert.strictEqual(form.$('.img.btn-info').length, 0,
            "No image should be selected");

        // select first image
        form.$(".img.img-fluid:first").click();
        assert.ok(form.$(".img.img-fluid:first").hasClass('btn-info'),
            "First image should be selected");

        form.destroy();
    });
});
});
});
