odoo.define('base.settings_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');
var AbstractStorageService = require('web.AbstractStorageService');
var RamStorage = require('web.RamStorage');

var createView = testUtils.createView;
var BaseSettingsView = view_registry.get('base_settings');
var createActionManager = testUtils.createActionManager;

var LocalStorageServiceMock;

QUnit.module('base_settings_tests', {
    beforeEach: function () {
        this.data = {
            project: {
                fields: {
                    foo: {string: "Foo", type: "boolean"},
                    bar: {string: "Bar", type: "boolean"},
                },
            },
        };
        LocalStorageServiceMock = AbstractStorageService.extend({storage: new RamStorage()});
    }
}, function () {

    QUnit.module('BaseSetting');

    QUnit.test('change setting on nav bar click in base settings', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: BaseSettingsView,
            model: 'project',
            data: this.data,
            arch: '<form string="Settings" class="oe_form_configuration o_base_settings">' +
                    '<div class="o_panel">' +
                        '<div class="setting_search">' +
                            '<input type="text" class="searchInput" placeholder="Search..."/>' +
                        '</div> ' +
                    '</div> ' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Cancel" type="object" name="cancel" class="oe_link" />' +
                    '</header>' +
                    '<div class="o_setting_container">' +
                        '<div class="settings_tab"/>'+
                        '<div class="settings">' +
                            '<div class="notFound o_hidden">No Record Found</div>' +
                            '<div class="app_settings_block" string="CRM" data-key="crm">' +
                                '<div class="row mt16 o_settings_container">'+
                                    '<div class="col-12 col-lg-6 o_setting_box">'+
                                        '<div class="o_setting_left_pane">' +
                                            '<field name="bar"/>'+
                                        '</div>'+
                                        '<div class="o_setting_right_pane">'+
                                            '<label for="bar"/>'+
                                            '<div class="text-muted">'+
                                                'this is bar'+
                                            '</div>'+
                                        '</div>' +
                                    '</div>'+
                                    '<div class="col-12 col-lg-6 o_setting_box">'+
                                        '<div class="o_setting_left_pane">' +
                                            '<field name="foo"/>'+
                                        '</div>'+
                                        '<div class="o_setting_right_pane">'+
                                            '<label for="foo"/>'+
                                            '<div class="text-muted">'+
                                                'this is foo'+
                                            '</div>'+
                                        '</div>' +
                                    '</div>'+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</form>',
        });

        assert.hasAttrValue(form.$('.selected'), 'data-key',"crm","crm setting selected");
        assert.isVisible(form.$(".settings .app_settings_block"), "project settings show");
        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'b', 'keyup');
        assert.strictEqual($('.highlighter').html(),"B","b word hilited");
        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'bx', 'keyup');
        assert.isVisible(form.$('.notFound'), "record not found message shown");
        form.destroy();
    });

    QUnit.test('settings views does not read existing id when coming back in breadcrumbs', async function (assert) {
        assert.expect(8);

        var actions = [{
            id: 1,
            name: 'Settings view',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[1, 'form']],
        }, {
            id: 4,
            name: 'Other action',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
        }];
        var archs = {
            'project,1,form': '<form string="Settings" js_class="base_settings">' +
                    '<div class="app_settings_block" string="CRM" data-key="crm">' +
                        '<button name="4" string="Execute action" type="action"/>' +
                    '</div>' +
                '</form>',
            'project,2,list': '<tree><field name="foo"/></tree>',
            'project,false,search': '<search></search>',
        };

        var actionManager = await createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(1);
        await testUtils.nextTick();
        await testUtils.dom.click(actionManager.$('button[name="4"]'));
        await testUtils.dom.click($('.o_control_panel .breadcrumb-item a'));
        assert.hasClass(actionManager.$('.o_form_view'), 'o_form_editable');
        assert.verifySteps([
            'load_views', // initial setting action
            'default_get', // this is a setting view => create new record
            'create', // when we click on action button => save
            'read', // with save, we have a reload... (not necessary actually)
            'load_views', // for other action in breadcrumb,
                    // with a searchread (not shown here since it is a route)
            'default_get', // when we come back, we want to restart from scratch
        ]);

        actionManager.destroy();
    });

    QUnit.test('save the data before open any action in settings view', async function (assert) {
        assert.expect(7);

        var actions = [{
            id: 1,
            name: 'Settings view',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[1, 'form']],
        }, {
            id: 4,
            name: 'Other action',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
        }];
        var archs = {
            'project,1,form': '<form string="Settings" js_class="base_settings">' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute"/>' +
                    '</header>' +
                    '<div class="app_settings_block" string="CRM" data-key="crm">' +
                        '<button name="4" string="Execute action" type="action"/>' +
                    '</div>' +
                '</form>',
            'project,2,list': '<tree><field name="foo"/></tree>',
            'project,false,search': '<search></search>',
        };

        var actionManager = await createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
            services: {
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_button') {
                    return Promise.resolve();
                }
                if (args.method) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
        });
        testUtils.mock.intercept(actionManager, 'execute_action', function (event) {
            assert.step(event.data.action_data.name);
        });

        await actionManager.doAction(1);
        await testUtils.nextTick();
        await testUtils.dom.click(actionManager.$('button[name="4"]'));
        var local_storage_data = actionManager.call('local_storage', 'getItem', 'buttonClickedEvent');
        assert.strictEqual(local_storage_data.attrs.name, "4" , "Should store data which having button name 4 in localstorage");
        assert.verifySteps([
            'load_views', // initial setting action
            'default_get', // this is a setting view => create new record
            'create', // when we click on action button => save
            'read', // with save, we have a reload... (not necessary actually)
            'execute', // save record before open action
        ]);
        actionManager.destroy();
    });

    QUnit.test('settings view does not display other settings after reload', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: BaseSettingsView,
            model: 'project',
            data: this.data,
            arch: '<form string="Settings" class="oe_form_configuration o_base_settings">' +
                    '<div class="o_panel">' +
                        '<div class="setting_search">' +
                            '<input type="text" class="searchInput" placeholder="Search..."/>' +
                        '</div> ' +
                    '</div> ' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Cancel" type="object" name="cancel" class="oe_link" />' +
                    '</header>' +
                    '<div class="o_setting_container">' +
                        '<div class="settings_tab"/>'+
                        '<div class="settings">' +
                            '<div class="notFound o_hidden">No Record Found</div>' +
                            '<div class="app_settings_block" string="CRM" data-key="crm">' +
                                'crm tab' +
                            '</div>' +
                            '<div class="app_settings_block o_not_app" string="Other App" data-key="otherapp">' +
                                'other app tab' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</form>',
        });

        assert.strictEqual(form.$('.app_settings_block').text().replace(/\s/g,''), 'CRMcrmtab');
        await form.reload();
        assert.strictEqual(form.$('.app_settings_block').text().replace(/\s/g,''), 'CRMcrmtab');
        form.destroy();
    });

});
});
