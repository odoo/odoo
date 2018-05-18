odoo.define('web.search_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;

QUnit.module('Mobile Search view Screen', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    boolean_field: {string: "I am a boolean", type: "boolean"},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop"},
                ],
            },
        };

        this.actions = [{
            id: 1,
            name: 'Partners Action 1',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list']],
        }];

        this.archs = {
            // list views
            'partner,false,list': '<tree><field name="foo"/></tree>',

            // search views
            'partner,false,search': '<search>' +
                    '<filter string="Active" name="my_projects" domain="[(\'boolean_field\', \'=\', True)]"/>' +
                    '<field name="foo" string="Foo"/>' +
                '</search>',
        };
    },
}, function () {
    QUnit.test('can activate a filter with mobile search view', function (assert) {
        assert.expect(3);

        var filterActiveFlag = false;

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (filterActiveFlag) {
                    assert.deepEqual(args.domain, [['boolean_field', '=', true]],
                        "domain should have been properly transferred to list view");
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.doAction(1);

        assert.ok(!$('.o_mobile_search').is(':visible'),
            'mobile search view is not visible');
        // open the search view
        $('button.o_enable_searchview').click();

        assert.ok($('.o_mobile_search').is(':visible'),
            'mobile search view is visible');

        // open filter sub menu
        $('button.o_dropdown_toggler_btn').first().click();

        filterActiveFlag = true;

        // click on Active filter
        $('.o_filters_menu a:contains(Active)').click();

        actionManager.destroy();
    });

});

});
