odoo.define('web.action_manager_mobile_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;

QUnit.module('ActionManager', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
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
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
        }, {
            id: 2,
            name: 'Partners Action 2',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [false, 'form']],
        }];

        this.archs = {
            // kanban views
            'partner,false,kanban': '<kanban><templates><t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
                '</t></templates></kanban>',

            // list views
            'partner,false,list': '<tree><field name="foo"/></tree>',

            // form views
            'partner,false,form': '<form>' +
                    '<group>' +
                        '<field name="display_name"/>' +
                    '</group>' +
                '</form>',

            // search views
            'partner,false,search': '<search><field name="foo" string="Foo"/></search>',
        };
    },
}, function () {
    QUnit.test('uses a mobile-friendly view by default (if possible)', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        // should default on a mobile-friendly view (kanban) for action 1
        actionManager.doAction(1);

        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should not have rendered the list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should have rendered the kanban view");

        // there is no mobile-friendly view for action 2, should use the first one (list)
        actionManager.doAction(2);

        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should have rendered the list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 0,
            "there should be no kanban view in the DOM");

        actionManager.destroy();
    });

    QUnit.test('lazy load mobile-friendly view', function (assert) {
        assert.expect(11);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.loadState({
            action: 1,
            view_type: 'form',
        });

        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should not have rendered a list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 0,
            "should not have rendered a kanban view either");
        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should have rendered a form view");

        // go back to lazy loaded view
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual(actionManager.$('.o_form_view').length, 0,
            "should not display the form view anymore");
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should not display the list view either");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should have lazy loaded the kanban view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'default_get', // default_get to open form view
            '/web/dataset/search_read', // search read when coming back to Kanban
        ]);

        actionManager.destroy();
    });

    QUnit.test('view switcher button should be displayed in dropdown on mobile screens', function (assert) {
        assert.expect(3);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);

        assert.ok($('.o_control_panel .o_cp_switch_buttons button[data-toggle="dropdown"]').length, 1,
            "view switcher button should be displayed");
        assert.ok($('.o_cp_switch_buttons .o_cp_switch_kanban').hasClass('active'),
            "kanban should be the active view");
        assert.ok($('.o_cp_switch_buttons .o_switch_view_button_icon').hasClass('fa-th-large'),
            "view switcher button icon should be an icon of the kanban");

        actionManager.destroy();
    });
});

});
