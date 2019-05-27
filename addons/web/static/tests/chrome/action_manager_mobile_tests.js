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
    QUnit.test('uses a mobile-friendly view by default (if possible)', async function (assert) {
        assert.expect(4);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        // should default on a mobile-friendly view (kanban) for action 1
        await actionManager.doAction(1);

        assert.containsNone(actionManager, '.o_list_view');
        assert.containsOnce(actionManager, '.o_kanban_view');

        // there is no mobile-friendly view for action 2, should use the first one (list)
        await actionManager.doAction(2);

        assert.containsOnce(actionManager, '.o_list_view');
        assert.containsNone(actionManager, '.o_kanban_view');

        actionManager.destroy();
    });

    QUnit.test('lazy load mobile-friendly view', async function (assert) {
        assert.expect(11);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await actionManager.loadState({
            action: 1,
            view_type: 'form',
        });

        assert.containsNone(actionManager, '.o_list_view');
        assert.containsNone(actionManager, '.o_kanban_view');
        assert.containsOnce(actionManager, '.o_form_view');

        // go back to lazy loaded view
        await testUtils.dom.click(actionManager.$('.o_control_panel .breadcrumb .breadcrumb-item:first'));
        assert.containsNone(actionManager, '.o_form_view');
        assert.containsNone(actionManager, '.o_list_view');
        assert.containsOnce(actionManager, '.o_kanban_view');

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'default_get', // default_get to open form view
            '/web/dataset/search_read', // search read when coming back to Kanban
        ]);

        actionManager.destroy();
    });

    QUnit.test('view switcher button should be displayed in dropdown on mobile screens', async function (assert) {
        assert.expect(3);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);

        assert.containsOnce(actionManager.$('.o_control_panel'), '.o_cp_switch_buttons button[data-toggle="dropdown"]');
        assert.hasClass(actionManager.$('.o_cp_switch_buttons .o_cp_switch_kanban'), 'active');
        assert.hasClass(actionManager.$('.o_cp_switch_buttons .o_switch_view_button_icon'), 'fa-th-large');

        actionManager.destroy();
    });
});

});
