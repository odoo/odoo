/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    makeDeferred,
    mockTimeout,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { editSearch } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { SettingsFormCompiler } from "@web/webclient/settings_form_view/settings_form_compiler";
import { registerCleanup } from "../../helpers/cleanup";

let target;
let serverData;
let execTimeouts;

QUnit.assert.areEquivalent = function (template1, template2) {
    if (template1.replace(/\s/g, "") === template2.replace(/\s/g, "")) {
        QUnit.assert.ok(true);
    } else {
        QUnit.assert.strictEqual(template1, template2);
    }
};

QUnit.module("SettingsFormView", (hooks) => {
    hooks.beforeEach(() => {
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
        const { execRegisteredTimeouts } = mockTimeout();
        execTimeouts = () => {
            execRegisteredTimeouts();
            return nextTick();
        };
    });

    QUnit.test("change setting on nav bar click in base settings", async function (assert) {
        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <app string="CRM" name="crm">
                        <setting type="header" string="Foo">
                            <field name="foo" title="Foo?."/>
                            <button name="nameAction" type="object" string="Button" class="col-auto btn-link ms-2 text-nowrap" style="line-height: 0.5;"/>
                        </setting>
                        <block title="Title of group Bar">
                            <setting help="this is bar" documentation="/applications/technical/web/settings/this_is_a_test.html">
                                <field name="bar"/>
                                <button name="buttonName" icon="fa-arrow-right" type="action" string="Manage Users" class="btn-link"/>
                            </setting>
                            <setting>
                                <label string="Big BAZ" for="baz"/>
                                <div class="text-muted">this is a baz</div>
                                <field name="baz"/>
                                <label>label with content</label>
                            </setting>
                        </block>
                        <block title="Title of group Foo">
                            <setting help="this is foo">
                                <field name="foo"/>
                            </setting>
                            <setting string="Personalize setting" help="this is full personalize setting">
                                <div>This is a different setting</div>
                            </setting>
                        </block>
                        <block title="Hide group Foo" attrs="{'invisible': [('bar','=',False)]}">
                            <setting string="Hide Foo" help="this is hide foo">
                                <field name="foo"/>
                            </setting>
                        </block>
                    </app>
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
            [...target.querySelectorAll(".settings .o_settings_container .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Bar", "Big BAZ", "Foo", "Personalize setting"]
        );
        assert.deepEqual(
            [...target.querySelectorAll(".settings .text-muted")].map((x) => x.textContent),
            ["this is bar", "this is a baz", "this is foo", "this is full personalize setting"]
        );
        assert.deepEqual(
            [...target.querySelectorAll(".settings h2:not(.d-none)")].map((x) => x.textContent),
            ["Title of group Bar", "Title of group Foo"]
        );
        assert.doesNotHaveClass(target.querySelector(".o_form_editable"), "o_form_nosheet");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_searchview input"),
            "searchview input should be focused"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );
        assert.strictEqual(
            target.querySelector(".o_setting_box a").href,
            "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_a_test.html"
        );

        await editSearch(target, "Hello there");
        await execTimeouts();
        assert.strictEqual(
            target.querySelector(".o_searchview input").value,
            "Hello there",
            "input value should be updated"
        );
        assert.containsNone(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "b");
        await execTimeouts();
        assert.strictEqual(
            target.querySelector(".highlighter").textContent,
            "B",
            "b word highlighted"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Bar", "Big BAZ"],
            "Foo is not shown"
        );

        assert.deepEqual(
            [...target.querySelectorAll(".settings h2:not(.d-none)")].map((x) => x.textContent),
            ["Title of group Bar"],
            "The title of group Bar is also selected"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "Big");
        await execTimeouts();
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container  .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Big BAZ"],
            "Only 'Big Baz' is shown"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".settings h2:not(.d-none)")].map((x) => x.textContent),
            ["Title of group Bar"],
            "The title of group Bar is also selected"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "Manage Us");
        await execTimeouts();
        assert.strictEqual(
            target.querySelector(".highlighter").textContent,
            "Manage Us",
            "Manage Us word highlighted"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Bar"],
            "Foo is not shown"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "group Bar");
        await execTimeouts();
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container  .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Bar", "Big BAZ"],
            "When searching a title, all group is shown"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "different");
        await execTimeouts();
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container  .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Personalize setting"],
            "When searching a title, all group is shown"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "bx");
        await execTimeouts();
        await nextTick();
        assert.isVisible(
            target.querySelector(".o_nocontent_help"),
            "record not found message shown"
        );
        assert.containsNone(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "Fo");
        await execTimeouts();
        assert.strictEqual(
            target.querySelector(".highlighter").textContent,
            "Fo",
            "Fo word highlighted"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            ["Foo", "Personalize setting"],
            "only settings in group Foo is shown"
        );
        assert.containsOnce(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );

        await editSearch(target, "Hide");
        await execTimeouts();
        assert.deepEqual(
            [...target.querySelectorAll(".settings h2:not(.d-none)")].map((x) => x.textContent),
            [],
            "Hide settings should not be shown"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_settings_container .o_setting_box .o_form_label")].map(
                (x) => x.textContent
            ),
            [],
            "Hide settings should not be shown"
        );
        assert.containsNone(
            target,
            ".app_settings_block:not(.d-none) .app_settings_header .o_setting_box"
        );
    });

    QUnit.test("unhighlight section not matching anymore", async function (assert) {
        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <app string="CRM" name="crm">
                        <block title="Baz">
                            <field name="baz" class="o_light_label" widget="radio"/>
                        </block>
                    </app>
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
        await execTimeouts();
        assert.containsN(target, ".highlighter", 2, "should have 2 options highlighted");
        assert.deepEqual(
            [...target.querySelectorAll(".highlighter")].map((x) => x.parentElement.textContent),
            ["treads", "treats"]
        );

        await editSearch(target, "tread");
        await execTimeouts();
        assert.containsN(target, ".highlighter", 1, "should have only one highlighted");
        assert.deepEqual(
            [...target.querySelectorAll(".highlighter")].map((x) => x.parentElement.textContent),
            ["treads"]
        );
    });

    QUnit.test("hide / show setting tips properly", async function (assert) {
        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <app string="Settings" name="settings">
                        <block title="Setting Header" help="Settings will appear below">
                            <setting help="this is bar">
                                <field name="bar"/>
                            </setting>
                        </block>
                        <block title="Title of group Foo">
                            <setting help="this is foo">
                                <field name="foo"/>
                            </setting>
                        </block>
                    </app>
                </form>`,
        });
        assert.containsOnce(
            target,
            ".o_setting_tip:not(.d-none)",
            "Tip should not be hidden initially"
        );
        await editSearch(target, "below");
        await execTimeouts();
        assert.containsOnce(target, ".o_setting_tip:not(.d-none)", "Tip should not be hidden");
        await editSearch(target, "Foo");
        await execTimeouts();
        assert.containsNone(target, ".o_setting_tip:not(.d-none)", "Tip should not be displayed");
        await editSearch(target, "");
        await execTimeouts();
        assert.containsOnce(target, ".o_setting_tip:not(.d-none)", "Tip should not be hidden");
    });

    QUnit.test(
        "settings views does not read existing id when coming back in breadcrumbs",
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
                        <app string="CRM" name="crm">
                            <block>
                                <setting help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                            <button name="4" string="Execute action" type="action"/>
                        </app>
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
            assert.notOk(target.querySelector(".o_field_boolean input").disabled);
            await click(target.querySelector("button[name='4']"));
            assert.strictEqual(
                target.querySelector(".breadcrumb").textContent,
                "SettingsOther action"
            );
            await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
            assert.notOk(target.querySelector(".o_field_boolean input").disabled);
            assert.verifySteps([
                "get_views", // initial setting action
                "onchange", // this is a setting view => new record transient record
                "create", // create the record before doing the action
                "read", // read the created record
                "get_views", // for other action in breadcrumb,
                "web_search_read", // with a searchread
                "onchange", // when we come back, we want to restart from scratch
            ]);
        }
    );

    QUnit.test("settings views does not read existing id when reload", async function (assert) {
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
                target: "new",
                type: "ir.actions.act_window",
                views: [["view_ref", "form"]],
            },
        };

        serverData.views = {
            "res.config.settings,1,form": `
                    <form string="Settings" js_class="base_settings">
                        <app string="CRM" name="crm">
                            <block>
                                <setting title="Foo" help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                            <button name="4" string="Execute action" type="action"/>
                        </app>
                    </form>`,
            "task,view_ref,form": `
                    <form>
                        <field name="display_name"/>
                    </form>`,
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

        assert.verifySteps([
            "get_views", // initial setting action
            "onchange", // this is a setting view => new record transient record
        ]);

        await click(target.querySelector("button[name='4']"));

        assert.verifySteps([
            "create", // settings: create the record before doing the action
            "read", // settings: read the created record
            "get_views", // dialog: get views
            "onchange", // dialog: onchange
        ]);

        await click(target, ".modal button.btn.btn-primary.o_form_button_save");
        assert.verifySteps([
            "create", // dialog: create the record before doing back to the settings
            "read", // dialog: read the created record
            "onchange", // settings: when we come back, we want to restart from scratch
        ]);
    });

    QUnit.test("Auto save: don't save on closing tab/browser", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <app string="Base Setting" name="base-setting">
                        <setting>
                            <field name="bar"/>Make Changes
                        </setting>
                    </app>
                </form>`,
            mockRPC(route, { args, method, model }) {
                if (method === "create" && model === "res.config.settings") {
                    assert.notOk(args, "settings should not be saved");
                }
            },
        });

        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );
        assert.containsNone(target, ".o_dirty_warning", "warning message should not be shown");
        await click(target.querySelector(".o_field_boolean input[id=bar]"));
        assert.containsOnce(target, ".o_field_boolean input:checked", "checkbox should be checked");

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();
    });

    QUnit.test("correctly copy attributes to compiled labels", async function (assert) {
        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form string="Settings" js_class="base_settings">
                    <app string="CRM" name="crm">
                        <block>
                            <setting>
                                <label for="foo" string="Label Before" class="a"/>
                                <field name="foo" class="b"/>
                                <label for="foo" string="Label After" class="c"/>
                            </setting>
                        </block>
                    </app>
                </form>`,
        });

        assert.hasClass(target.querySelectorAll(".o_form_label")[0], "a");
        assert.hasClass(target.querySelector(".o_field_widget.o_field_boolean"), "b");
        assert.hasClass(target.querySelectorAll(".o_form_label")[1], "c");
    });

    QUnit.test("settings views does not write the id on the url", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "Settings view",
                res_model: "res.config.settings",
                type: "ir.actions.act_window",
                views: [[1, "form"]],
            },
        };

        serverData.views = {
            "res.config.settings,1,form": `
                    <form string="Settings" js_class="base_settings">
                        <app string="CRM" name="crm">
                            <block>
                                <setting help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                        </app>
                    </form>`,
            "task,2,list": `
                    <tree>
                        <field name="display_name"/>
                    </tree>`,
            "res.config.settings,false,search": "<search></search>",
            "task,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (route === "/web/dataset/call_button") {
                if (args.method === "execute") {
                    return true;
                }
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);
        assert.notOk(target.querySelector(".o_field_boolean input").disabled);
        await click(target.querySelector(".o_field_boolean input"));
        assert.containsOnce(target, ".o_field_boolean input:checked", "checkbox should be checked");
        await click(target.querySelector(".o_form_button_save"));

        await nextTick();
        assert.notOk(webClient.env.services.router.current.hash.id);
    });

    QUnit.test(
        "settings views can search when coming back in breadcrumbs",
        async function (assert) {
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
                        <app string="CRM" name="crm">
                            <block>
                                <setting help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                            <button name="4" string="Execute action" type="action"/>
                        </app>
                    </form>`,
                "task,2,list": `
                    <tree>
                        <field name="display_name"/>
                    </tree>`,
                "res.config.settings,false,search": "<search></search>",
                "task,false,search": "<search></search>",
            };

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 1);
            await click(target.querySelector("button[name='4']"));
            await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
            await editSearch(target, "Fo");
            await execTimeouts();
            assert.strictEqual(
                target.querySelector(".highlighter").textContent,
                "Fo",
                "Fo word highlighted"
            );
        }
    );

    QUnit.test("search for default label when label has empty string", async function (assert) {
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
                        <app string="CRM" name="crm">
                            <block>
                                <setting>
                                    <label for="foo" string=""/>
                                    <field name="foo"/>
                                </setting>
                            </block>
                        </app>
                    </form>`,
            "task,2,list": `
                    <tree>
                        <field name="display_name"/>
                    </tree>`,
            "res.config.settings,false,search": "<search></search>",
            "task,false,search": "<search></search>",
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_form_label");
        assert.equal(target.querySelector(".o_form_label").textContent, "");
        assert.containsNone(target, ".app_settings_block:not(.d-none) .settingSearchHeader");
        await editSearch(target, "Fo");
        await execTimeouts();
        assert.containsNone(target, ".o_form_label");
        assert.containsNone(target, ".app_settings_block:not(.d-none) .settingSearchHeader");
    });

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
                        <app string="CRM" name="crm">
                            <block>
                                <setting string="Foo" help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                            <button name="4" string="Execute action" type="action"/>
                        </app>
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

            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                ".o_field_boolean input:checked",
                "checkbox should be checked"
            );

            await click(target.querySelector("button[name='4']"));
            assert.containsOnce(document.body, ".modal", "should open a warning dialog");

            await click(target.querySelectorAll(".modal-footer .btn")[2]); // Discard
            await nextTick();
            assert.containsOnce(target, ".o_list_view", "should be open list view");
            await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
            assert.containsNone(
                target,
                ".o_field_boolean input:checked",
                "checkbox should not be checked"
            );

            await click(target.querySelector(".o_field_boolean input"));
            await click(target.querySelector("button[name='4']"));
            assert.containsOnce(document.body, ".modal", "should open a warning dialog");

            await click(target.querySelectorAll(".modal-footer .btn")[1]); // Stay Here
            assert.containsOnce(target, ".o_form_view", "should be remain on form view");

            await click(target.querySelector(".o_form_button_save")); // Form Save button
            assert.containsNone(document.body, ".modal", "should not open a warning dialog");
            assert.notOk(target.querySelector(".o_field_boolean input").disabled); // Everything must stay in edit

            await click(target.querySelector(".o_field_boolean input"));
            await click(target.querySelector(".o_form_button_cancel")); // Form Discard button
            assert.containsNone(document.body, ".modal", "should not open a warning dialog");
        }
    );

    QUnit.test("clicking a button with dirty settings -- save", async (assert) => {
        registry.category("services").add(
            "action",
            {
                start() {
                    return {
                        doActionButton(params) {
                            assert.step(`action executed ${JSON.stringify(params)}`);
                        },
                    };
                },
            },
            { force: true }
        );
        await makeView({
            type: "form",
            arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <field name="foo" />
                        <button type="object" name="mymethod" class="myBtn"/>
                    </app>
                </form>`,
            serverData,
            resModel: "res.config.settings",
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "onchange"]);
        await click(target, ".o_field_boolean input[type='checkbox']");
        await click(target, ".myBtn");
        await click(target, ".modal .btn-primary");
        assert.verifySteps([
            "create",
            "read",
            'action executed {"name":"execute","type":"object","resModel":"res.config.settings","resIds":[1],"context":{"lang":"en","uid":7,"tz":"taht"},"buttonContext":{}}',
        ]);
    });

    QUnit.test("clicking a button with dirty settings -- discard", async (assert) => {
        registry.category("services").add(
            "action",
            {
                start() {
                    return {
                        doActionButton(params) {
                            assert.step(`action executed ${JSON.stringify(params)}`);
                        },
                    };
                },
            },
            { force: true }
        );
        await makeView({
            type: "form",
            arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <field name="foo" />
                        <button type="object" name="mymethod" class="myBtn"/>
                    </app>
                </form>`,
            serverData,
            resModel: "res.config.settings",
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "onchange"]);
        await click(target, ".o_field_boolean input[type='checkbox']");
        await click(target, ".myBtn");
        await click(target.querySelectorAll(".modal .btn-secondary")[1]);
        assert.verifySteps([
            "create",
            "read",
            'action executed {"context":{"lang":"en","uid":7,"tz":"taht"},"type":"object","name":"mymethod","resModel":"res.config.settings","resIds":[1],"buttonContext":{}}',
        ]);
    });

    QUnit.test(
        "clicking on a button with noSaveDialog will not show discard warning",
        async function (assert) {
            assert.expect(4);

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
                        <app string="CRM" name="crm">
                            <block>
                                <setting string="Foo" help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                            <button name="4" string="Execute action" type="action" noSaveDialog="true"/>
                        </app>
                    </form>`,
                "task,2,list": '<tree><field name="display_name"/></tree>',
                "res.config.settings,false,search": "<search></search>",
                "task,false,search": "<search></search>",
            };

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 1);
            assert.containsNone(
                target,
                ".o_field_boolean input:checked",
                "checkbox should not be checked"
            );

            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                ".o_field_boolean input:checked",
                "checkbox should be checked"
            );

            await click(target.querySelector("button[name='4']"));
            assert.containsNone(document.body, ".modal", "should not open a warning dialog");

            assert.containsOnce(target, ".o_list_view", "should be open list view");
        }
    );

    QUnit.test("settings view does not display o_not_app settings", async function (assert) {
        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                    <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                        <app string="CRM" name="crm">
                            <block title="CRM">
                                <setting help="this is bar">
                                    <field name="bar"/>
                                </setting>
                            </block>
                        </app>
                        <app notApp="1" string="Other App" name="otherapp">
                            <h2>Other app tab</h2>
                            <block>
                                <setting help="this is bar">
                                    <field name="bar"/>
                                </setting>
                            </block>
                        </app>
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
                    <app string="Base Setting" name="base-setting">
                        <setting>
                            <field name="bar"/>Make Changes
                        </setting>
                    </app>
                </form>`,
        });

        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );
        assert.containsNone(target, ".o_dirty_warning", "warning message should not be shown");
        await click(target.querySelector(".o_field_boolean input[id=bar]"));
        assert.containsOnce(target, ".o_field_boolean input:checked", "checkbox should be checked");
        assert.containsOnce(target, ".o_dirty_warning", "warning message should be shown");
    });

    QUnit.test(
        "settings view shows a message if there are changes even if the save failed",
        async function (assert) {
            const self = this;
            self.alreadySavedOnce = false;
            await makeView({
                type: "form",
                resModel: "res.config.settings",
                serverData,
                mockRPC: function (route, args) {
                    if (args.method === "create" && !self.alreadySavedOnce) {
                        self.alreadySavedOnce = true;
                        //fail on first create
                        return Promise.reject({});
                    }
                },
                arch: `
                    <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                        <app string="Base Setting" name="base-setting">
                            <setting>
                                <field name="bar"/>Make Changes
                            </setting>
                        </app>
                    </form>`,
            });

            await click(target.querySelector("input[id=bar]"));
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
                        <app string="CRM" name="crm">
                            <block title="Title of group">
                                <setting>
                                    <button name="3" string="Execute action" type="action"/>
                                </setting>
                            </block>
                        </app>
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
            assert.strictEqual($(target).find(".breadcrumb").text(), "First actionSettings");

            def = makeDeferred();
            await click(target.querySelector('button[name="3"]'));
            assert.strictEqual($(target).find(".breadcrumb").text(), "First actionSettings");

            def.resolve();
            await nextTick();
            assert.strictEqual(
                $(target).find(".breadcrumb").text(),
                "First actionSettingsOther action"
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
                    <app string="Base Setting" name="base-setting">
                        <setting>
                            <field name="tasks">
                                <tree><field name="display_name"/></tree>
                                <form><field name="display_name"/></form>
                            </field>
                        </setting>
                    </app>
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
            assert.expect(6);

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
                        <app string="CRM" name="crm">
                            <block>
                                <setting string="Foo" help="this is foo">
                                    <field name="foo"/>
                                </setting>
                                <button name="4" string="Execute action" type="action"/>
                            </block>
                        </app>
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

            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                ".o_field_boolean input:checked",
                "checkbox should be checked"
            );

            await click(target.querySelector('button[name="4"]'));
            assert.containsOnce(target, ".modal", "should open a warning dialog");

            await click(target.querySelector(".modal-footer .btn-primary"));
            assert.verifySteps([
                "create", // saveRecord from modal
                "execute", // execute_action
            ]);
        }
    );
    QUnit.test("Discard button clean the settings view", async function (assert) {
        assert.expect(10);

        serverData.actions = {
            1: {
                id: 1,
                name: "Settings view",
                res_model: "res.config.settings",
                type: "ir.actions.act_window",
                views: [[1, "form"]],
            },
        };

        serverData.views = {
            "res.config.settings,1,form": `
                    <form string="Settings" js_class="base_settings">
                        <app string="CRM" name="crm">
                            <block>
                                <setting string="Foo" help="this is foo">
                                    <field name="foo"/>
                                </setting>
                            </block>
                        </app>
                    </form>
                `,
            "res.config.settings,false,search": "<search></search>",
            "task,false,list": "<tree></tree>",
            "task,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            assert.step(args.method || route);
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
        ]);
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );

        await click(target.querySelector(".o_field_boolean input"));
        assert.containsOnce(target, ".o_field_boolean input:checked", "checkbox should be checked");

        await click(target.querySelector(".o_form_button_cancel"));

        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );
        assert.verifySteps(["onchange"]);
    });

    QUnit.test("Settings Radio widget: show and search", async function (assert) {
        serverData.models["res.config.settings"].fields.product_id = {
            string: "Product",
            type: "many2one",
            relation: "product",
        };
        serverData.models.product = {
            fields: {
                name: { string: "Product Name", type: "char" },
            },
            records: [
                {
                    id: 37,
                    display_name: "xphone",
                },
                {
                    id: 41,
                    display_name: "xpad",
                },
            ],
        };
        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <app string="CRM" name="crm">
                        <block>
                            <setting>
                                <label for="product_id"/>
                                <div class="content-group">
                                    <div class="mt16">
                                        <field name="product_id" class="o_light_label" widget="radio"/>
                                    </div>
                                </div>
                            </setting>
                        </block>
                    </app>
                </form>`,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_radio_item label")].map(
                (x) => x.parentElement.textContent
            ),
            ["xphone", "xpad"]
        );

        await editSearch(target, "xp");
        await execTimeouts();
        assert.containsN(target, ".highlighter", 2, "should have 2 options highlighted");
        assert.deepEqual(
            [...target.querySelectorAll(".highlighter")].map((x) => x.parentElement.textContent),
            ["xphone", "xpad"]
        );

        await editSearch(target, "xph");
        await execTimeouts();
        assert.containsN(target, ".highlighter", 1, "should have only one highlighted");
        assert.deepEqual(
            [...target.querySelectorAll(".highlighter")].map((x) => x.parentElement.textContent),
            ["xphone"]
        );
    });

    QUnit.test("standalone field labels with string inside a settings page", async (assert) => {
        let compiled = undefined;
        patchWithCleanup(SettingsFormCompiler.prototype, {
            compile() {
                const _compiled = this._super(...arguments);
                compiled = _compiled;
                return _compiled;
            },
        });

        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <setting>
                            <label string="My&quot; little &apos;  Label" for="display_name" class="highhopes"/>
                            <field name="display_name" />
                        </setting>
                    </app>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector("label.highhopes").textContent,
            "My\" little '  Label"
        );

        const expectedCompiled = `
            <SettingsPage slots="{NoContentHelper:this.props.slots.NoContentHelper}" initialTab="this.props.initialApp" t-slot-scope="settings" modules="[{&quot;key&quot;:&quot;crm&quot;,&quot;string&quot;:&quot;CRM&quot;,&quot;imgurl&quot;:&quot;/crm/static/description/icon.png&quot;}]">
                <SettingsApp key="\`crm\`" string="\`CRM\`" imgurl="\`/crm/static/description/icon.png\`" selectedTab="settings.selectedTab">
                    <Setting title="\`\`"  help="\`\`" companyDependent="false" documentation="\`\`" record="this.props.record" string="\`\`" addLabel="true" labels="[&quot;\`My\\&quot; little '  Label\`&quot;]">
                        <FormLabel id="'display_name'" fieldName="'display_name'" record="this.props.record" fieldInfo="this.props.archInfo.fieldNodes['display_name']" className="&quot;highhopes&quot;" string="\`My&quot; little '  Label\`"/>
                        <Field id="'display_name'" name="'display_name'" record="this.props.record" fieldInfo="this.props.archInfo.fieldNodes['display_name']"/>
                    </Setting>
                </SettingsApp>
            </SettingsPage>`;
        assert.areEquivalent(compiled.firstChild.innerHTML, expectedCompiled);
    });

    QUnit.test("highlight Element with inner html/fields", async (assert) => {
        let compiled = undefined;
        patchWithCleanup(SettingsFormCompiler.prototype, {
            compile() {
                const _compiled = this._super(...arguments);
                compiled = _compiled;
                return _compiled;
            },
        });

        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <setting>
                            <field name="bar"/>
                            <div class="text-muted">this is Baz value: <field name="baz" readonly="1"/> and this is the after text</div>
                        </setting>
                    </block>
                </app>
            </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_setting_right_pane .text-muted").textContent,
            "this is Baz value: treads and this is the after text"
        );

        const expectedCompiled = `
            <HighlightText originalText="\`this is Baz value: \`"/>
            <Field id="'baz'" name="'baz'" record="this.props.record" fieldInfo="this.props.archInfo.fieldNodes['baz']"/>
            <HighlightText originalText="\` and this is the after text\`"/>`;
        assert.areEquivalent(
            compiled.querySelector("Setting div.text-muted").innerHTML,
            expectedCompiled
        );
    });

    QUnit.test("settings form doesn't autofocus", async (assert) => {
        serverData.models["res.config.settings"].fields.textField = { type: "char" };

        const onFocusIn = (ev) => {
            assert.step(`focusin: ${ev.target.outerHTML}`);
        };
        document.addEventListener("focusin", onFocusIn);
        registerCleanup(() => {
            document.removeEventListener("focusin", onFocusIn);
        });

        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <setting>
                            <field name="textField"/>
                        </setting>
                    </block>
                </app>
            </form>`,
        });

        assert.containsOnce(target, "[name='textField'] input");
        assert.verifySteps([
            `focusin: <input type="text" class="o_searchview_input" accesskey="Q" placeholder="Search..." role="searchbox">`,
        ]);
    });

    QUnit.test("settings form keeps scrolling by app", async (assert) => {
        const oldHeight = target.style.getPropertyValue("height");
        target.style.setProperty("height", "200px");
        registerCleanup(() => {
            target.style.setProperty("height", oldHeight);
        });

        await makeView({
            type: "form",
            resModel: "res.config.settings",
            serverData,
            arch: `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                        <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                        <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                        <div id="deepDivCrm" />
                    </block>
                </app>

                <app string="OtherApp" name="otherapp">
                    <block title="Title of group Other">
                        <setting>
                            <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                            <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                            <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                            <div id="deepDivOther" />
                        </setting>
                    </block>
                </app>
            </form>`,
        });

        // constrain o_content to have height for its children to be scrollable
        target.querySelector(".o_content").style.setProperty("height", "200px");

        const scrollingEl = target.querySelector(".settings");
        assert.strictEqual(scrollingEl.scrollTop, 0);

        await click(target.querySelector(".settings_tab [data-key='otherapp']"));
        assert.strictEqual(scrollingEl.scrollTop, 0);
        target.querySelector("#deepDivOther").scrollIntoView();

        const scrollTop = scrollingEl.scrollTop;
        assert.ok(scrollTop > 0);

        await click(target.querySelector(".settings_tab [data-key='crm']"));
        assert.strictEqual(scrollingEl.scrollTop, 0);

        await click(target.querySelector(".settings_tab [data-key='otherapp']"));
        assert.strictEqual(scrollingEl.scrollTop, scrollTop);
    });
});
