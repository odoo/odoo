odoo.define('base.settings_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var createView = testUtils.createView;
var BaseSettingsView = view_registry.get('base_settings');
var createActionManager = testUtils.createActionManager;


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
    }
}, function () {

    QUnit.module('BaseSetting');

    QUnit.test('change setting on nav bar click in base settings', async function (assert) {
        assert.expect(5);

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
                                            '<span class="o_form_label">Foo</span>'+
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
        assert.strictEqual(form.$('.highlighter').html(), "B", "b word highlighted");
        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'bx', 'keyup');
        assert.isVisible(form.$('.notFound'), "record not found message shown");
        form.$('.searchInput').val('f').trigger('keyup');
        assert.strictEqual(form.$('span.o_form_label .highlighter').html(), "F", "F word highlighted");
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
            'onchange', // this is a setting view => create new record
            'create', // when we click on action button => save
            'read', // with save, we have a reload... (not necessary actually)
            'load_views', // for other action in breadcrumb,
                    // with a searchread (not shown here since it is a route)
            'onchange', // when we come back, we want to restart from scratch
        ]);

        actionManager.destroy();
    });

    QUnit.test('clicking on any button in setting should show discard warning if setting form is dirty', async function (assert) {
        assert.expect(11);

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
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Cancel" type="object" name="cancel" class="oe_link" />' +
                    '</header>' +
                    '<div class="app_settings_block" string="CRM" data-key="crm">' +
                        '<div class="row mt16 o_settings_container">'+
                            '<div class="col-12 col-lg-6 o_setting_box">'+
                                '<div class="o_setting_left_pane">' +
                                    '<field name="foo"/>'+
                                '</div>'+
                                '<div class="o_setting_right_pane">'+
                                    '<span class="o_form_label">Foo</span>'+
                                        '<div class="text-muted">'+
                                            'this is foo'+
                                        '</div>'+
                                '</div>' +
                            '</div>'+
                        '</div>'+
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
                if (route === '/web/dataset/call_button') {
                    if (args.method === "execute") {
                        assert.ok("execute method called");
                        return Promise.resolve(true);
                    }
                    if (args.method === "cancel") {
                        assert.ok("cancel method called");
                        return Promise.resolve(true);
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(1);
        assert.containsNone(actionManager, '.o_field_boolean input:checked',
            "checkbox should not be checked");

        await testUtils.dom.click(actionManager.$("input[type='checkbox']"));
        assert.containsOnce(actionManager, '.o_field_boolean input:checked',
            "checkbox should be checked");

        await testUtils.dom.click(actionManager.$('button[name="4"]'));
        assert.containsOnce(document.body, '.modal', "should open a warning dialog");

        await testUtils.dom.click($('.modal button:contains(Ok)'));
        assert.containsOnce(actionManager, '.o_list_view', "should be open list view");

        await testUtils.dom.click($('.o_control_panel .breadcrumb-item a'));
        assert.containsNone(actionManager, '.o_field_boolean input:checked',
            "checkbox should not be checked");

        await testUtils.dom.click(actionManager.$("input[type='checkbox']"));
        await testUtils.dom.click(actionManager.$('button[name="4"]'));
        assert.containsOnce(document.body, '.modal', "should open a warning dialog");

        await testUtils.dom.click($('.modal button:contains(Cancel)'));
        assert.containsOnce(actionManager, '.o_form_view' ,"should be remain on form view");

        await testUtils.dom.click(actionManager.$("button[name='execute']"));
        assert.containsNone(document.body, '.modal', "should not open a warning dialog");

        await testUtils.dom.click(actionManager.$("input[type='checkbox']"));
        await testUtils.dom.click(actionManager.$("button[name='cancel']"));
        assert.containsNone(document.body, '.modal', "should not open a warning dialog");

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

    QUnit.test('settings view shows a message if there are changes', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: BaseSettingsView,
            model: 'project',
            data: this.data,
            arch: '<form string="Settings" class="oe_form_configuration o_base_settings">' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Discard" type="object" name="cancel" special="cancel" />'+
                    '</header>' +
                    '<div class="o_setting_container">' +
                        '<div class="settings_tab"/>' +
                        '<div class="settings">' +
                            '<div class="notFound o_hidden">No Record Found</div>' +
                            '<div class="app_settings_block" string="Base Setting" data-key="base-setting">' +
                                '<field name="bar"/>Make Changes' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</form>',
        });

        testUtils.mock.intercept(form, "field_changed", function (event) {
            assert.ok(true,"field changed");
        }, true);

        assert.containsNone(form, '.o_field_boolean input:checked', "checkbox should not be checked");
        assert.containsNone(form, ".o_dirty_warning", "warning message should not be shown");
        await testUtils.dom.click(form.$("input[type='checkbox']"));
        assert.containsOnce(form, '.o_field_boolean input:checked' ,"checkbox should be checked");
        assert.containsOnce(form, ".o_dirty_warning", "warning message should be shown");
        form.destroy();
    });

    QUnit.test('settings view shows a message if there are changes even if the save failed', async function (assert) {
        assert.expect(3);
        var self = this;
        self.alreadySavedOnce = false;

        var form = await createView({
            View: BaseSettingsView,
            model: 'project',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === "create" && !self.alreadySavedOnce) {
                    self.alreadySavedOnce = true;
                    //fail on first create
                    return Promise.reject({});
                }
                return this._super.apply(this, arguments);
            },
            arch: '<form string="Settings" class="oe_form_configuration o_base_settings">' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Discard" type="object" name="cancel" special="cancel" />'+
                    '</header>' +
                    '<div class="o_setting_container">' +
                        '<div class="settings_tab"/>' +
                        '<div class="settings">' +
                            '<div class="notFound o_hidden">No Record Found</div>' +
                            '<div class="app_settings_block" string="Base Setting" data-key="base-setting">' +
                                '<field name="bar"/>Make Changes' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</form>',
        });


        await testUtils.dom.click(form.$("input[type='checkbox']"));
        assert.containsOnce(form, ".o_dirty_warning", "warning message should be shown");
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, ".o_dirty_warning", "warning message should be shown");
        await testUtils.form.clickSave(form);
        assert.containsNone(form, ".o_dirty_warning", "warning message should be shown");

        form.destroy();
    });

    QUnit.test('execute action from settings view with several actions in the breadcrumb', async function (assert) {
        // This commit fixes a race condition, that's why we artificially slow down a read rpc
        assert.expect(4);

        const actions = [{
            id: 1,
            name: 'First action',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[1, 'list']],
        }, {
            id: 2,
            name: 'Settings view',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[2, 'form']],
        }, {
            id: 3,
            name: 'Other action',
            res_model: 'project',
            type: 'ir.actions.act_window',
            views: [[3, 'list']],
        }];
        const archs = {
            'project,1,list': '<tree><field name="foo"/></tree>',
            'project,2,form': `
                <form string="Settings" js_class="base_settings">
                    <div class="app_settings_block" string="CRM" data-key="crm">
                        <button name="3" string="Execute action" type="action"/>
                    </div>
                </form>`,
            'project,3,list': '<tree><field name="foo"/></tree>',
            'project,false,search': '<search></search>',
        };

        let loadViewsDef;
        const actionManager = await createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
            async mockRPC(route, args) {
                const _super = this._super.bind(this);
                if (args.method === 'read') {
                    await Promise.resolve(loadViewsDef); // slow down reload of settings view
                }
                return _super(route, args);
            },
        });

        await actionManager.doAction(1);
        assert.strictEqual(actionManager.$('.breadcrumb').text(), 'First action');

        await actionManager.doAction(2);
        assert.strictEqual(actionManager.$('.breadcrumb').text(), 'First actionNew');

        loadViewsDef = testUtils.makeTestPromise();
        await testUtils.dom.click(actionManager.$('button[name="3"]'));
        assert.strictEqual(actionManager.$('.breadcrumb').text(), 'First actionNew');

        loadViewsDef.resolve();
        await testUtils.nextTick();
        assert.strictEqual(actionManager.$('.breadcrumb').text(), 'First actionNewOther action');

        actionManager.destroy();
    });
});
});
