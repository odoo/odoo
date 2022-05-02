/** @odoo-module **/

import { click, editInput, getFixture, makeDeferred, nextTick } from "@web/../tests/helpers/utils";
import { editSearch } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

let target, serverData;

QUnit.module(
    "SettingsFormView",
    {
        beforeEach: function () {
            serverData = {
                models: {
                    "res.config.settings": {
                        fields: {
                            foo: { string: "Foo", type: "boolean" },
                            bar: { string: "Bar", type: "boolean" },
                            tasks: { string: "one2many field", type: "one2many", relation: "task" },
                            baz: {
                                string: "Baz",
                                type: "selection",
                                selection: [
                                    [1, "treads"],
                                    [2, "treats"],
                                ],
                                default: 1,
                            },
                        },
                    },
                    task: {
                        fields: {},
                    },
                },
            };
            target = getFixture();
            setupViewRegistries();
        },
    },
    function () {
        QUnit.test("change setting on nav bar click in base settings", async function (assert) {
            await makeView({
                type: "form",
                resModel: "res.config.settings",
                serverData,
                arch: `
                    <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                        <div class="o_setting_container">
                            <div class="settings">
                                <div class="app_settings_block" string="CRM" data-key="crm">
                                    <h2>Title of group Bar</h2>
                                    <div class="row mt16 o_settings_container">
                                        <div class="col-12 col-lg-6 o_setting_box">
                                            <div class="o_setting_left_pane">
                                                <field name="bar"/>
                                            </div>
                                            <div class="o_setting_right_pane">
                                                <label for="bar"/>
                                                <div class="text-muted">this is bar</div>
                                            </div>
                                        </div>
                                        <div class="col-12 col-lg-6 o_setting_box">
                                            <div class="o_setting_left_pane">
                                                <field name="bar"/>
                                            </div>
                                            <div class="o_setting_right_pane">
                                                <label for="bar" string="This is Big BAR"/>
                                                <div class="text-muted">this is big bar</div>
                                            </div>
                                        </div>
                                    </div>
                                    <h2>Title of group Foo</h2>
                                    <div class="row mt16 o_settings_container">
                                        <div class="col-12 col-lg-6 o_setting_box">
                                            <div class="o_setting_left_pane">
                                                <field name="foo"/>
                                            </div>
                                            <div class="o_setting_right_pane">
                                                <span class="o_form_label">Foo</span>
                                                <div class="text-muted">this is foo</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>`,
            });

            assert.hasAttrValue(
                target.querySelector(".selected"),
                "data-key",
                "crm",
                "crm setting selected"
            );
            assert.isVisible(
                target.querySelector(".settings .app_settings_block"),
                "res.config.settings settings show"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".settings .o_form_label")].map((x) => x.textContent),
                ["Bar", "This is Big BAR", "Foo"]
            );
            assert.deepEqual(
                [...target.querySelectorAll(".settings .text-muted")].map((x) => x.textContent),
                ["this is bar", "this is big bar", "this is foo"]
            );
            assert.deepEqual(
                [...target.querySelectorAll(".settings h2")].map((x) => x.textContent),
                ["Title of group Bar", "Title of group Foo"]
            );
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_searchview input"),
                "searchview input should be focused"
            );

            await editSearch(target, "Hello there");
            assert.strictEqual(
                target.querySelector(".o_searchview input").value,
                "Hello there",
                "input value should be updated"
            );

            await editSearch(target, "b");
            assert.strictEqual(
                target.querySelector(".highlighter").textContent,
                "B",
                "b word highlighted"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".o_setting_box .o_form_label")].map(
                    (x) => x.textContent
                ),
                ["Bar", "This is Big BAR"],
                "Foo is not shown"
            );

            assert.deepEqual(
                [...target.querySelectorAll(".settings h2")].map((x) => x.textContent),
                ["Title of group Bar"],
                "The title of group Bar is also selected"
            );

            await editSearch(target, "Big");
            assert.deepEqual(
                [...target.querySelectorAll(".o_setting_box .o_form_label")].map(
                    (x) => x.textContent
                ),
                ["This is Big BAR"],
                "Only 'Big Bar' is shown"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".settings h2")].map((x) => x.textContent),
                ["Title of group Bar"],
                "The title of group Bar is also selected"
            );

            await editSearch(target, "group Bar");
            assert.deepEqual(
                [...target.querySelectorAll(".o_setting_box .o_form_label")].map(
                    (x) => x.textContent
                ),
                ["Bar", "This is Big BAR"],
                "When searching a title, all group is shown"
            );

            await editSearch(target, "bx");
            await nextTick();
            assert.isVisible(
                target.querySelector(".o_nocontent_help"),
                "record not found message shown"
            );
            await editSearch(target, "Fo");
            assert.strictEqual(
                target.querySelector(".highlighter").textContent,
                "Fo",
                "F word highlighted"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".o_setting_box .o_form_label")].map(
                    (x) => x.textContent
                ),
                ["Foo"],
                "only Foo is shown"
            );
        });

        QUnit.test("unhighlight section not matching anymore", async function (assert) {
            await makeView({
                type: "form",
                resModel: "res.config.settings",
                serverData,
                arch: `
                    <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                        <div class="o_setting_container">
                            <div class="settings">
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
                    </form>`,
            });
            assert.hasAttrValue(
                target.querySelector(".selected"),
                "data-key",
                "crm",
                "crm setting selected"
            );
            assert.isVisible(
                target.querySelector(".settings .app_settings_block"),
                "project settings show"
            );

            await editSearch(target, "trea");
            assert.containsN(target, ".highlighter", 2, "should have 2 options highlighted");
            assert.deepEqual(
                [...target.querySelectorAll(".highlighter")].map(
                    (x) => x.parentElement.textContent
                ),
                ["treads", "treats"]
            );

            await editSearch(target, "tread");
            assert.containsN(target, ".highlighter", 1, "should have only one highlighted");
            assert.deepEqual(
                [...target.querySelectorAll(".highlighter")].map(
                    (x) => x.parentElement.textContent
                ),
                ["treads"]
            );
        });

        QUnit.test(
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
                    "res.config.settings,1,form": `
                        <form string="Settings" js_class="base_settings">
                            <div class="settings">
                                <div class="app_settings_block" string="CRM" data-key="crm">
                                    <div class="row mt16 o_settings_container">
                                        <div class="col-12 col-lg-6 o_setting_box">
                                            <div class="o_setting_left_pane">
                                                <field name="foo"/>
                                            </div>
                                            <div class="o_setting_right_pane">
                                                <span class="o_form_label">Foo</span>
                                                <div class="text-muted">this is foo</div>
                                            </div>
                                        </div>
                                    </div>
                                    <button name="4" string="Execute action" type="action"/>
                                </div>
                            </div>
                        </form>`,
                    "task,2,list": `
                        <tree>
                            <field name="display_name"/>
                        </tree>`,
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
                assert.notOk(target.querySelector(".custom-checkbox input").disabled);
                await click(target.querySelector("button[name='4']"));
                await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
                assert.notOk(target.querySelector(".custom-checkbox input").disabled);
                assert.verifySteps([
                    "get_views", // initial setting action
                    "onchange", // this is a setting view => create new record
                    "get_views", // for other action in breadcrumb,
                    "web_search_read", // with a searchread
                    "onchange", // when we come back, we want to restart from scratch
                ]);
            }
        );

        QUnit.test(
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
                    "res.config.settings,1,form": `
                        <form string="Settings" js_class="base_settings">
                            <div class="settings">
                                <div class="app_settings_block" string="CRM" data-key="crm">
                                    <div class="row mt16 o_settings_container">
                                        <div class="col-12 col-lg-6 o_setting_box">
                                            <div class="o_setting_left_pane">
                                                <field name="foo"/>
                                            </div>
                                            <div class="o_setting_right_pane">
                                                <span class="o_form_label">Foo</span>
                                                <div class="text-muted">this is foo</div>
                                            </div>
                                        </div>
                                    </div>
                                    <button name="4" string="Execute action" type="action"/>
                                </div>
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
                    }
                };

                const webClient = await createWebClient({ serverData, mockRPC });

                await doAction(webClient, 1);
                assert.containsNone(
                    target,
                    ".o_field_boolean input:checked",
                    "checkbox should not be checked"
                );

                await click(target.querySelector(".custom-checkbox input"));
                assert.containsOnce(
                    target,
                    ".o_field_boolean input:checked",
                    "checkbox should be checked"
                );

                await click(target.querySelector("button[name='4']"));
                assert.containsOnce(document.body, ".modal", "should open a warning dialog");

                await click(target.querySelectorAll(".modal-footer .btn")[1]); // Discard
                await nextTick();
                assert.containsOnce(target, ".o_list_view", "should be open list view");
                await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
                assert.containsNone(
                    target,
                    ".o_field_boolean input:checked",
                    "checkbox should not be checked"
                );

                await click(target.querySelector(".custom-checkbox input"));
                await click(target.querySelector("button[name='4']"));
                assert.containsOnce(document.body, ".modal", "should open a warning dialog");

                await click(target.querySelectorAll(".modal-footer .btn")[2]); // Stay Here
                assert.containsOnce(target, ".o_form_view", "should be remain on form view");

                await click(target.querySelector(".o_form_button_save")); // Form Save button
                assert.containsNone(document.body, ".modal", "should not open a warning dialog");
                assert.notOk(target.querySelector(".custom-checkbox input").disabled); // Everything must stay in edit

                await click(target.querySelector(".custom-checkbox input"));
                await click(target.querySelector(".o_form_button_cancel")); // Form Discard button
                assert.containsNone(document.body, ".modal", "should not open a warning dialog");
            }
        );

        QUnit.test("settings view does not display o_not_app settings", async function (assert) {
            await makeView({
                type: "form",
                resModel: "res.config.settings",
                serverData,
                arch: `
                        <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                            <div class="o_setting_container">
                                <div class="settings">
                                    <div class="app_settings_block" string="CRM" data-key="crm">
                                        <h2>CRM</h2>
                                        <div class="row mt16 o_settings_container">
                                            <div class="col-12 col-lg-6 o_setting_box">
                                                <div class="o_setting_left_pane">
                                                    <field name="bar"/>
                                                </div>
                                                <div class="o_setting_right_pane">
                                                    <label for="bar"/>
                                                    <div class="text-muted">this is bar</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="app_settings_block o_not_app" string="Other App" data-key="otherapp">
                                        <h2>Other app tab</h2>
                                        <div class="row mt16 o_settings_container">
                                            <div class="col-12 col-lg-6 o_setting_box">
                                                <div class="o_setting_left_pane">
                                                    <field name="bar"/>
                                                </div>
                                                <div class="o_setting_right_pane">
                                                    <label for="bar"/>
                                                    <div class="text-muted">this is bar</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </form>`,
            });

            assert.deepEqual(
                [...target.querySelectorAll(".app_name")].map((x) => x.textContent),
                ["CRM"]
            );

            assert.deepEqual(
                [...target.querySelectorAll(".settings .o_form_label")].map((x) => x.textContent),
                ["Bar"]
            );
        });

        QUnit.test("settings view shows a message if there are changes", async function (assert) {
            await makeView({
                type: "form",
                resModel: "res.config.settings",
                serverData,
                arch: `
                    <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                        <div class="o_setting_container">
                            <div class="settings">
                                <div class="app_settings_block" string="Base Setting" data-key="base-setting">
                                    <div class="o_setting_box">
                                        <field name="bar"/>Make Changes
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>`,
            });

            assert.containsNone(
                target,
                ".o_field_boolean input:checked",
                "checkbox should not be checked"
            );
            assert.containsNone(target, ".o_dirty_warning", "warning message should not be shown");
            await click(target.querySelector("input.custom-control-input[id='field_bar_1']"));
            assert.containsOnce(
                target,
                ".o_field_boolean input:checked",
                "checkbox should be checked"
            );
            assert.containsOnce(target, ".o_dirty_warning", "warning message should be shown");
        });

        QUnit.test(
            "settings view shows a message if there are changes even if the save failed",
            async function (assert) {
                await makeView({
                    type: "form",
                    resModel: "res.config.settings",
                    serverData,
                    mockRPC: function (route, args) {
                        if (route === "/web/dataset/call_button") {
                            if (args.method === "execute") {
                                return Promise.reject({});
                            }
                        }
                    },
                    arch: `
                        <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                            <div class="o_setting_container">
                                <div class="settings">
                                    <div class="app_settings_block" string="Base Setting" data-key="base-setting">
                                        <div class="o_setting_box">
                                            <field name="bar"/>Make Changes
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </form>`,
                });

                await click(target.querySelector("input[id='field_bar_1']"));
                assert.containsOnce(target, ".o_dirty_warning", "warning message should be shown");
                await click(target.querySelector(".o_form_button_save"));
                assert.containsOnce(target, ".o_dirty_warning", "warning message should be shown");
            }
        );

        QUnit.test(
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
                            <div class="settings">
                                <div class="app_settings_block" string="CRM" data-key="crm">
                                    <button name="3" string="Execute action" type="action"/>
                                </div>
                            </div>
                        </form>`,
                    "task,3,list": '<tree><field name="display_name"/></tree>',
                    "res.config.settings,false,search": "<search></search>",
                    "task,false,search": "<search></search>",
                };

                let def;
                const mockRPC = async (route, args) => {
                    if (args.method === "web_search_read") {
                        await def; // slow down reload of settings view
                    }
                };

                const webClient = await createWebClient({ serverData, mockRPC });
                await doAction(webClient, 1);
                assert.strictEqual($(target).find(".breadcrumb").text(), "First action");

                await doAction(webClient, 2);
                assert.strictEqual($(target).find(".breadcrumb").text(), "Settings");

                def = makeDeferred();
                await click(target.querySelector('button[name="3"]'));
                assert.strictEqual($(target).find(".breadcrumb").text(), "Settings");

                def.resolve();
                await nextTick();
                assert.strictEqual(
                    $(target).find(".breadcrumb").text(),
                    "First actionNewOther action"
                );
            }
        );

        QUnit.test("settings can contain one2many fields", async function (assert) {
            await makeView({
                type: "form",
                resModel: "res.config.settings",
                serverData,
                arch: `
                    <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                        <div class="o_setting_container">
                            <div class="settings">
                                <div class="app_settings_block" string="Base Setting" data-key="base-setting">
                                    <div class="o_setting_box">
                                        <field name="tasks">
                                            <tree><field name="display_name"/></tree>
                                            <form><field name="display_name"/></form>
                                       </field>
                                   </div>
                               </div>
                           </div>
                        </div>
                    </form>`,
            });

            await click(target.querySelector(".o_field_x2many_list_row_add a"));
            await editInput(target, ".modal-body input", "Added Task");
            await click(target.querySelector(".modal-footer .btn.o_form_button_save"));

            assert.strictEqual(
                target.querySelector("table.o_list_table tr.o_data_row").textContent,
                "Added Task",
                "The one2many relation item should have been added"
            );
        });

        QUnit.test(
            'call "call_button/execute" when clicking on a button in dirty settings',
            async function (assert) {
                assert.expect(5);

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
                    },
                };

                serverData.views = {
                    "res.config.settings,1,form": `
                        <form string="Settings" js_class="base_settings">
                            <div class="settings">
                                <div class="app_settings_block" string="CRM" data-key="crm">
                                    <div class="row mt16 o_settings_container">
                                        <div class="col-12 col-lg-6 o_setting_box">
                                            <div class="o_setting_left_pane">
                                                <field name="foo"/>
                                            </div>
                                            <div class="o_setting_right_pane">
                                                <span class="o_form_label">Foo</span>
                                                <div class="text-muted">this is foo</div>
                                            </div>
                                        </div>
                                        <button name="4" string="Execute action" type="action"/>
                                    </div>
                                </div>
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

                await click(target.querySelector(".custom-checkbox input"));
                assert.containsOnce(
                    target,
                    ".o_field_boolean input:checked",
                    "checkbox should be checked"
                );

                await click(target.querySelector('button[name="4"]'));
                assert.containsOnce(target, ".modal", "should open a warning dialog");

                await click(target.querySelector(".modal-footer .btn-primary"));
                assert.verifySteps([
                    "execute", // execute_action
                ]);
            }
        );
    }
);
