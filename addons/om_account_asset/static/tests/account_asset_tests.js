odoo.define('om_account_asset.widget_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('om_account_asset', {
    beforeEach: function () {
        this.data = {
            asset: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    line_ids: {
                        string: "Lines",
                        type: "one2many",
                        relation: 'line',
                        relation_field: 'asset_id',
                    },
                },
                records: [{
                    id: 1,
                    display_name: "asset name",
                    line_ids: [1, 2, 3, 4],
                }],
            },
            line: {
                fields: {
                    move_check: {string: "Move Check", type: 'boolean'},
                    move_posted_check: {string: "Move Posted Check", type: 'boolean'},
                    asset_id: {string: "Asset", type: 'many2one', relation: 'asset'},
                },
                records: [{
                    id: 1,
                    move_check: true,
                    move_posted_check: true,
                }, {
                    id: 2,
                    move_check: false,
                    move_posted_check: true,
                }, {
                    id: 3,
                    move_check: true,
                    move_posted_check: false,
                }, {
                    id: 4,
                    move_check: false,
                    move_posted_check: false,
                }],
            },
        };
    }
});

QUnit.test('basic rendering', function (assert) {
    assert.expect(18);

    var form = createView({
        View: FormView,
        model: 'asset',
        data: this.data,
        arch: '<form string="Asset">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="line_ids">' +
                        '<tree>' +
                            '<field name="move_check" widget="deprec_lines_toggler"/>' +
                            '<field name="move_posted_check" invisible="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
    });

    // check the header
    assert.strictEqual(form.$('thead th').text(), "", "toggler column should have no title");

    // check the classnames
    assert.ok(form.$('.o_deprec_lines_toggler_cell:nth(0) button').hasClass('o_is_posted'),
        "first line toggler should have classname 'o_is_posted'");
    assert.ok(!form.$('.o_deprec_lines_toggler_cell:nth(0) button').hasClass('o_unposted'),
        "first line toggler should not have classname 'o_unposted'");

    assert.ok(form.$('.o_deprec_lines_toggler_cell:nth(1) button').hasClass('o_is_posted'),
        "second line toggler should have classname 'o_is_posted'");
    assert.ok(!form.$('.o_deprec_lines_toggler_cell:nth(1) button').hasClass('o_unposted'),
        "second line toggler should not have classname 'o_unposted'");

    assert.ok(!form.$('.o_deprec_lines_toggler_cell:nth(2) button').hasClass('o_is_posted'),
        "third line toggler should not have classname 'o_is_posted'");
    assert.ok(form.$('.o_deprec_lines_toggler_cell:nth(2) button').hasClass('o_unposted'),
        "third line toggler should have classname 'o_unposted'");

    assert.ok(!form.$('.o_deprec_lines_toggler_cell:nth(3) button').hasClass('o_is_posted'),
        "fourth line toggler should not have classname 'o_is_posted'");
    assert.ok(!form.$('.o_deprec_lines_toggler_cell:nth(3) button').hasClass('o_unposted'),
        "fourth line toggler should not have classname 'o_unposted'");

    // check the titles
    assert.strictEqual(form.$('.o_deprec_lines_toggler_cell:nth(0) button').attr('title'),
        'Posted', "first line toggler should have correct title");
    assert.strictEqual(form.$('.o_deprec_lines_toggler_cell:nth(1) button').attr('title'),
        'Posted', "second line toggler should have correct title");
    assert.strictEqual(form.$('.o_deprec_lines_toggler_cell:nth(2) button').attr('title'),
        'Accounting entries waiting for manual verification',
        "third line toggler should have correct title");
    assert.strictEqual(form.$('.o_deprec_lines_toggler_cell:nth(3) button').attr('title'),
        'Unposted', "fourth line toggler should have correct title");

    // check disabled property
    assert.ok(form.$('.o_deprec_lines_toggler_cell:nth(0) button').attr('disabled'),
        "first line toggle should be disabled");
    assert.ok(form.$('.o_deprec_lines_toggler_cell:nth(1) button').attr('disabled'),
        "second line toggle should be disabled");
    assert.ok(form.$('.o_deprec_lines_toggler_cell:nth(2) button').attr('disabled'),
        "third line toggle should be disabled");
    assert.ok(!form.$('.o_deprec_lines_toggler_cell:nth(3) button').attr('disabled'),
        "fourth line toggle should not be disabled");

    // check the visibility: the widget should always be visible, regardless its value
    assert.strictEqual(form.$('.o_deprec_lines_toggler:visible').length, 4,
        "all togglers should be visible");

    form.destroy();
});

QUnit.test('click events are correctly triggered', function (assert) {
    assert.expect(2);

    var form = createView({
        View: FormView,
        model: 'asset',
        data: this.data,
        arch: '<form string="Asset">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="line_ids">' +
                        '<tree>' +
                            '<field name="move_check" widget="deprec_lines_toggler"/>' +
                            '<field name="move_posted_check" invisible="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        intercepts: {
            execute_action: function (event) {
                var data = event.data;
                assert.strictEqual(data.env.model, 'line', "should have correct model");
                assert.strictEqual(data.action_data.name, 'create_move',
                    "should call correct method");
            },
        }
    });

    // click on last row toggler
    form.$('.o_deprec_lines_toggler_cell:nth(3) button').click();

    form.destroy();
});

});

});
