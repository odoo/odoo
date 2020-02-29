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
    QUnit.test('can activate a filter with mobile search view in quick search mode', async function (assert) {
        assert.expect(7);

        var searchRPCFlag = false;

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (searchRPCFlag) {
                    assert.deepEqual(args.domain, [['foo', 'ilike', 'A']],
                        "domain should have been properly transferred to list view");
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(1);

        assert.strictEqual($('button.o_enable_searchview.fa-search').length, 1,
            "should display a button to open the searchview");
        assert.deepEqual($('.o_searchview_input_container:visible').length, 0,
            "Quick search input should be hidden");

        // open the search view
        await testUtils.dom.click($('button.o_enable_searchview'));
        assert.deepEqual($('.o_toggle_searchview_full:visible').length, 1,
            "should display a button to expand the searchview");
        assert.deepEqual($('.o_searchview_input_container:visible').length, 1,
            "Quick search input should now be visible");

        searchRPCFlag = true;

        // use quick search input
        $('.o_searchview_input')
            .val("A")
            .trigger($.Event('keypress', { which: 65, keyCode: 65 }));
        await testUtils.nextTick();
        actionManager.$('.o_searchview_input')
            .trigger($.Event('keydown', { which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();

        // close quick search
        await testUtils.dom.click($('button.o_enable_searchview.fa-close'));
        assert.deepEqual($('.o_toggle_searchview_full:visible').length, 0,
            "Expand icon shoud be hidden");
        assert.deepEqual($('.o_searchview_input_container:visible').length, 0,
            "Quick search input should be hidden");

        actionManager.destroy();
    });

    QUnit.test('can activate a filter with mobile search view in full screen mode', async function (assert) {
        assert.expect(4);

        var filterActiveFlag = false;

        var actionManager = await createActionManager({
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

        await actionManager.doAction(1);

        assert.ok(!$('.o_mobile_search').is(':visible'),
            'mobile search view is not visible');

        // open the search view
        await testUtils.dom.click($('button.o_enable_searchview'));
        // open it in full screen
        await testUtils.dom.click($('.o_toggle_searchview_full'));
        assert.ok($('.o_mobile_search').is(':visible'),
            'mobile search view is visible');

        // open filter sub menu
        await testUtils.dom.click($('button.o_dropdown_toggler_btn').first());
        filterActiveFlag = true;
        // click on Active filter
        await testUtils.dom.click($('.o_filters_menu a:contains(Active)'));

        // closing search view
        await testUtils.dom.click($('.o_mobile_search_close'));
        assert.ok(!$('.o_mobile_search').is(':visible'),
            'mobile search view is not visible');

        actionManager.destroy();
    });

});

});
