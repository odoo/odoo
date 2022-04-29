odoo.define('base.settings_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var createView = testUtils.createView;
var BaseSettingsView = view_registry.get('base_settings');

const { getFixture, legacyExtraNextTick } = require("@web/../tests/helpers/utils");
const { createWebClient, doAction } = require("@web/../tests/webclient/helpers");

let serverData;
let target;
QUnit.module('base_settings_tests', {
    beforeEach: function () {
        this.data = {
            'res.config.settings': {
                fields: {
                    foo: {string: "Foo", type: "boolean"},
                    bar: {string: "Bar", type: "boolean"},
                    tasks: {string: "one2many field", type: "one2many", relation: 'task'},
                    baz: {
                        string: "Baz",
                        type: "selection",
                        selection: [[1, "treads"], [2, "treats"]],
                        default: 1,
                    },
                },
            },
            'task': {
                fields: {}
            }
        };
        serverData = { models: this.data };
        target = getFixture();
    }
}, function () {

    QUnit.module('BaseSetting');

    QUnit.test('change setting on nav bar click in base settings', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: BaseSettingsView,
            model: 'res.config.settings',
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
        assert.isVisible(form.$(".settings .app_settings_block"), "res.config.settings settings show");
        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'b', 'keyup');
        assert.strictEqual(form.$('.highlighter').html(), "B", "b word highlighted");
        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'bx', 'keyup');
        assert.isVisible(form.$('.notFound'), "record not found message shown");
        form.$('.searchInput').val('f').trigger('keyup');
        assert.strictEqual(form.$('span.o_form_label .highlighter').html(), "F", "F word highlighted");
        form.destroy();
    });

    QUnit.test('unhighlight section not matching anymore', async function(assert) {
        assert.expect(7);

        const form = await createView({
            View: BaseSettingsView,
            model: 'res.config.settings',
            data: this.data,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings">
                    <div class="o_panel">
                        <div class="setting_search">
                            <input type="text" class="searchInput" placeholder="Search..." />
                        </div>
                    </div>
                    <header>
                        <button string="Save" type="object" name="execute" class="oe_highlight" />
                        <button string="Cancel" type="object" name="cancel" class="oe_link" />
                    </header>
                    <div class="o_setting_container">
                        <div class="settings_tab" />
                        <div class="settings">
                            <div class="notFound o_hidden">No Record Found</div>
                            <div class="app_settings_block" string="CRM" data-key="crm">
                                <div class="row mt16 o_settings_container">
                                    <div class="col-12 col-lg-6 o_setting_box">
                                        <div class="o_setting_right_pane">
                                            <label for="baz"/>
                                            <div class="content-group">
                                                <div class="mt16">
                                                    <field name="baz" class="o_light_label" widget="radio"/>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>`
        });
        assert.hasAttrValue(form.$('.selected'), 'data-key',"crm","crm setting selected");
        assert.isVisible(form.$(".settings .app_settings_block"), "project settings show");

        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'trea', 'keyup');
        assert.containsN(form, '.highlighter', 2, 'should have 2 options highlighted');
        assert.equal(form.$('.highlighter:eq(0)').parent().text(), 'treads');
        assert.equal(form.$('.highlighter:eq(1)').parent().text(), 'treats');

        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'tread', 'keyup');
        assert.containsN(form, '.highlighter', 1, 'should have only one highlighted');
        assert.equal(form.$('.highlighter').parent().text(), 'treads');

        form.destroy();
    });

    QUnit.skipWOWL('hide / show setting tips properly', async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: BaseSettingsView,
            model: 'res.config.settings',
            data: this.data,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings">
                    <div class="o_panel">
                        <div class="setting_search">
                            <input type="text" class="searchInput" placeholder="Search..." />
                        </div>
                    </div>
                    <div class="o_setting_container">
                        <div class="settings_tab" />
                        <div class="settings">
                            <div class="notFound o_hidden">No Record Found</div>
                            <div class="app_settings_block" string="Settings" data-key="settings">
                                <h2>Setting Header</h2>
                                <h3 class="o_setting_tip">Settings will appear below</h3>
                            </div>
                        </div>
                    </div>
                </form>`
        });

        assert.containsOnce(form, '.o_setting_tip:not(.o_hidden)', 'Tip should not be hidden initially');

        await testUtils.fields.editAndTrigger(form.$('.searchInput'), 'Setting', 'keyup');
        assert.containsOnce(form, '.o_setting_tip.o_hidden', 'Tip should be hidden when user searches in settings');

        await testUtils.fields.editAndTrigger(form.$('.searchInput'), '', 'keyup');
        assert.containsOnce(form, '.o_setting_tip:not(.o_hidden)', 'Tip should be displayed again');

        form.destroy();
    });

    QUnit.skipWOWL(
        "settings views does not read existing id when coming back in breadcrumbs",
        async function (assert) {
            assert.expect(8);

            serverData.actions = {
                1: {
                    id: 1,
                    name: "Settings view",
                    res_model: "res.config.settings",
                    type: "ir.actions.act_window",
                    views: [[1, "form"]],
                },
                4: {
                    id: 4,
                    name: "Other action",
                    res_model: "task",
                    type: "ir.actions.act_window",
                    views: [[2, "list"]],
                },
            };

            serverData.views = {
                "res.config.settings,1,form":
                    `<form string="Settings" js_class="base_settings">
                        <div class="app_settings_block" string="CRM" data-key="crm">
                            <button name="4" string="Execute action" type="action"/>
                        </div>
                    </form>`,
                "task,2,list": '<tree><field name="display_name"/></tree>',
                "res.config.settings,false,search": "<search></search>",
                "task,false,search": "<search></search>",
            };

            const mockRPC = (route, args) => {
                if (args.method) {
                    assert.step(args.method);
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, 1);
            await testUtils.dom.click($(target).find('button[name="4"]'));
            await legacyExtraNextTick();
            await testUtils.dom.click($(".o_control_panel .breadcrumb-item a"));
            await legacyExtraNextTick();
            assert.hasClass($(target).find(".o_form_view"), "o_form_editable");
            assert.verifySteps([
                "get_views", // initial setting action
                "onchange", // this is a setting view => create new record
                "create", // when we click on action button => save
                "read", // with save, we have a reload... (not necessary actually)
                "get_views", // for other action in breadcrumb,
                // with a searchread (not shown here since it is a route)
                "onchange", // when we come back, we want to restart from scratch
            ]);
        }
    );

    QUnit.skipWOWL(
        "clicking on any button in setting should show discard warning if setting form is dirty",
        async function (assert) {
            assert.expect(11);

            serverData.actions = {
                1: {
                    id: 1,
                    name: "Settings view",
                    res_model: "res.config.settings",
                    type: "ir.actions.act_window",
                    views: [[1, "form"]],
                },
                4: {
                    id: 4,
                    name: "Other action",
                    res_model: "task",
                    type: "ir.actions.act_window",
                    views: [[2, "list"]],
                },
            };

            serverData.views = {
                "res.config.settings,1,form":
                    `<form string="Settings" js_class="base_settings">
                        <header>
                            <button string="Save" type="object" name="execute" class="oe_highlight" />
                            <button string="Cancel" type="object" name="cancel" class="oe_link" />
                        </header>
                        <div class="app_settings_block" string="CRM" data-key="crm">
                            <div class="row mt16 o_settings_container">
                                <div class="col-12 col-lg-6 o_setting_box">
                                    <div class="o_setting_left_pane">
                                        <field name="foo"/>
                                    </div>
                                    <div class="o_setting_right_pane">
                                        <span class="o_form_label">Foo</span>
                                          <div class="text-muted">
                                            this is foo
                                          </div>
                                    </div>
                                </div>
                            </div>
                            <button name="4" string="Execute action" type="action"/>
                        </div>
                    </form>`,
                "task,2,list": '<tree><field name="display_name"/></tree>',
                "res.config.settings,false,search": "<search></search>",
                "task,false,search": "<search></search>",
            };

            const mockRPC = (route, args) => {
                if (route === "/web/dataset/call_button") {
                    if (args.method === "execute") {
                        assert.ok("execute method called");
                        return true;
                    }
                    if (args.method === "cancel") {
                        assert.ok("cancel method called");
                        return true;
                    }
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, 1);
            assert.containsNone(
                target,
                ".o_field_boolean input:checked",
                "checkbox should not be checked"
            );

            await testUtils.dom.click($(target).find("input[type='checkbox']"));
            assert.containsOnce(
                target,
                ".o_field_boolean input:checked",
                "checkbox should be checked"
            );

            await testUtils.dom.click($(target).find('button[name="4"]'));
            await legacyExtraNextTick();
            assert.containsOnce(document.body, ".modal", "should open a warning dialog");

            await testUtils.dom.click($(".modal button:contains(Discard)"));
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_list_view", "should be open list view");

            await testUtils.dom.click($(".o_control_panel .breadcrumb-item a"));
            await legacyExtraNextTick();
            assert.containsNone(
                target,
                ".o_field_boolean input:checked",
                "checkbox should not be checked"
            );

            await testUtils.dom.click($(target).find("input[type='checkbox']"));
            await testUtils.dom.click($(target).find('button[name="4"]'));
            await legacyExtraNextTick();
            assert.containsOnce(document.body, ".modal", "should open a warning dialog");

            await testUtils.dom.click($(".modal button:contains(Stay Here)"));
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_form_view", "should be remain on form view");

            await testUtils.dom.click($(target).find("button[name='execute']"));
            await legacyExtraNextTick();
            assert.containsNone(
                document.body,
                ".modal",
                "should not open a warning dialog"
            );

            await testUtils.dom.click($(target).find("input[type='checkbox']"));
            await testUtils.dom.click($(target).find("button[name='cancel']"));
            await legacyExtraNextTick();
            assert.containsNone(
                document.body,
                ".modal",
                "should not open a warning dialog"
            );
        }
    );

    QUnit.test('settings view does not display other settings after reload', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: BaseSettingsView,
            model: 'res.config.settings',
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
            model: 'res.config.settings',
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
            model: 'res.config.settings',
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

    QUnit.skipWOWL(
        "execute action from settings view with several actions in the breadcrumb",
        async function (assert) {
            // This commit fixes a race condition, that's why we artificially slow down a read rpc
            assert.expect(4);

            serverData.actions = {
                1: {
                    id: 1,
                    name: "First action",
                    res_model: "task",
                    type: "ir.actions.act_window",
                    views: [[1, "list"]],
                },
                2: {
                    id: 2,
                    name: "Settings view",
                    res_model: "res.config.settings",
                    type: "ir.actions.act_window",
                    views: [[2, "form"]],
                },
                3: {
                    id: 3,
                    name: "Other action",
                    res_model: "task",
                    type: "ir.actions.act_window",
                    views: [[3, "list"]],
                },
            };

            serverData.views = {
                "task,1,list": '<tree><field name="display_name"/></tree>',
                "res.config.settings,2,form": `
                    <form string="Settings" js_class="base_settings">
                        <div class="app_settings_block" string="CRM" data-key="crm">
                            <button name="3" string="Execute action" type="action"/>
                        </div>
                    </form>`,
                "task,3,list": '<tree><field name="display_name"/></tree>',
                "res.config.settings,false,search": "<search></search>",
                "task,false,search": "<search></search>",
            };

            let loadViewsDef;
            const mockRPC = async (route, args) => {
                if (args.method === "read") {
                    await loadViewsDef; // slow down reload of settings view
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 1);
            assert.strictEqual($(target).find(".breadcrumb").text(), "First action");

            await doAction(webClient, 2);
            assert.strictEqual(
                $(target).find(".breadcrumb").text(),
                "First actionNew"
            );

            loadViewsDef = testUtils.makeTestPromise();
            await testUtils.dom.click($(target).find('button[name="3"]'));
            await legacyExtraNextTick();
            assert.strictEqual(
                $(target).find(".breadcrumb").text(),
                "First actionNew"
            );

            loadViewsDef.resolve();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.strictEqual(
                $(target).find(".breadcrumb").text(),
                "First actionNewOther action"
            );
        }
    );

    QUnit.test('settings can contain one2many fields', async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: BaseSettingsView,
            model: 'res.config.settings',
            data: this.data,
            arch: `
                   <form string="Settings" class="oe_form_configuration o_base_settings">
                       <header>
                           <button string="Save" type="object" name="execute" class="oe_highlight" />
                           <button string="Discard" type="object" name="cancel" special="cancel" />
                       </header>
                       <div class="o_setting_container">
                           <div class="settings_tab"/>
                           <div class="settings">
                               <div class="notFound o_hidden">No Record Found</div>
                               <div class="app_settings_block" string="Base Setting" data-key="base-setting">
                                   <field name="tasks">
                                       <tree><field name="display_name"/></tree>
                                       <form><field name="display_name"/></form>
                                   </field>
                               </div>
                           </div>
                       </div>
                   </form>`,
        });

        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput($('.modal-body input[name=display_name]'), 'Added Task');
        await testUtils.dom.click($('.modal-dialog footer button:first-child'));

        assert.strictEqual(form.$('table.o_list_table:eq(0) tr.o_data_row td.o_data_cell:eq(0)').text(),
            'Added Task',
            'The one2many relation item should have been added');

        await testUtils.form.clickSave(form);

        assert.strictEqual(form.$('table.o_list_table:eq(0) tr.o_data_row td.o_data_cell:eq(0)').text(),
            'Added Task',
            'The one2many relation item should still be present');

        form.destroy();
    });

    QUnit.skipWOWL(
        'call "call_button/execute" when clicking on a button in dirty settings',
        async function (assert) {
            assert.expect(7);

            serverData.actions = {
                1: {
                    id: 1,
                    name: "Settings view",
                    res_model: "res.config.settings",
                    type: "ir.actions.act_window",
                    views: [[1, "form"]],
                },
                4: {
                    id: 4,
                    name: "Other Action",
                    res_model: "task",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                }
            };

            serverData.views = {
                "res.config.settings,1,form": `
                    <form string="Settings" js_class="base_settings">
                        <div class="app_settings_block" string="CRM" data-key="crm">
                            <div class="row mt16 o_settings_container">
                                <div class="col-12 col-lg-6 o_setting_box">
                                    <div class="o_setting_left_pane">
                                        <field name="foo"/>
                                    </div>
                                    <div class="o_setting_right_pane">
                                        <span class="o_form_label">Foo</span>
                                        <div class="text-muted">
                                            this is foo
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <button name="4" string="Execute action" type="action"/>
                        </div>
                    </form>
                `,
                "res.config.settings,false,search": "<search></search>",
                "task,false,list": "<tree></tree>",
                "task,false,search": "<search></search>",
            };

            const mockRPC = (route, args) => {
                if (route === "/web/dataset/call_button" && args.method === "execute") {
                    assert.step("execute");
                    return true;
                } else if (args.method === "create") {
                    assert.step("create");
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, 1);
            assert.containsNone(
                target,
                ".o_field_boolean input:checked",
                "checkbox should not be checked"
            );

            await testUtils.dom.click($(target).find('input[type="checkbox"]'));
            assert.containsOnce(
                target,
                ".o_field_boolean input:checked",
                "checkbox should be checked"
            );

            await testUtils.dom.click($(target).find('button[name="4"]'));
            assert.containsOnce(document.body, ".modal", "should open a warning dialog");

            await testUtils.dom.click($(".modal-footer .btn-primary"));
            assert.verifySteps([
                "create", // saveRecord from modal
                "execute", // execute_action
                "create", // saveRecord from FormController._onButtonClicked
            ]);
        }
    );

});
});
