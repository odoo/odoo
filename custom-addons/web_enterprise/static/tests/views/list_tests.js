/** @odoo-module */

import { getFixture, patchWithCleanup, click, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { session } from "@web/session";
import { ListRenderer } from "@web/views/list/list_renderer";
import { browser } from "@web/core/browser/browser";
import { patchListRendererDesktop } from "@web_enterprise/views/list/list_renderer_desktop";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { registry } from "@web/core/registry";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";

let config;
let serverData;
let target;
QUnit.module(
    "web_enterprise",
    {
        beforeEach() {
            target = getFixture();
            config = {
                actionId: 1,
                actionType: "ir.actions.act_window",
            };
            serverData = {
                models: {
                    foo: {
                        fields: {
                            foo: { string: "Foo", type: "char" },
                            bar: { string: "Bar", type: "boolean" },
                        },
                        records: [
                            { id: 1, bar: true, foo: "yop" },
                            { id: 2, bar: true, foo: "blip" },
                            { id: 3, bar: true, foo: "gnap" },
                            { id: 4, bar: false, foo: "blip" },
                        ],
                    },
                },
            };
            patchWithCleanup(ListRenderer.prototype, patchListRendererDesktop());

            setupViewRegistries();
        },
    },
    function () {
        QUnit.module("ListView");

        QUnit.test(
            "add custom field button with other optional columns - studio not installed",
            async function (assert) {
                assert.expect(11);

                patchWithCleanup(session, { is_system: true });

                await makeView({
                    serverData,
                    type: "list",
                    resModel: "foo",
                    arch: `
                        <tree>
                            <field name="foo"/>
                            <field name="bar" optional="hide"/>
                        </tree>`,
                    mockRPC(route, args) {
                        if (args.method === "search_read" && args.model === "ir.module.module") {
                            assert.step("studio_module_id");
                            return Promise.resolve([{ id: 42 }]);
                        }
                        if (
                            args.method === "button_immediate_install" &&
                            args.model === "ir.module.module"
                        ) {
                            assert.deepEqual(
                                args.args[0],
                                [42],
                                "Should be the id of studio module returned by the search read"
                            );
                            assert.step("studio_module_install");
                            return true;
                        }
                    },
                    config,
                });

                patchWithCleanup(browser.location, {
                    reload: function () {
                        assert.step("window_reload");
                    },
                });

                assert.containsN(target, ".o_data_row", 4);
                assert.containsOnce(target, ".o_optional_columns_dropdown_toggle");

                await click(target, ".o_optional_columns_dropdown_toggle");
                assert.containsN(target, ".o_optional_columns_dropdown .dropdown-item", 2);
                assert.containsOnce(target, ".o_optional_columns_dropdown .dropdown-item-studio");

                await click(target, ".o_optional_columns_dropdown .dropdown-item-studio");
                await nextTick();
                assert.containsOnce(target, ".modal-studio");

                await click(target, ".modal .o_install_studio");
                assert.equal(browser.localStorage.getItem("openStudioOnReload"), "main");
                assert.verifySteps(["studio_module_id", "studio_module_install", "window_reload"]);
            }
        );

        QUnit.test(
            "add custom field button without other optional columns - studio not installed",
            async function (assert) {
                assert.expect(11);

                patchWithCleanup(session, { is_system: true });

                await makeView({
                    serverData,
                    type: "list",
                    resModel: "foo",
                    config,
                    arch: `
                        <tree>
                            <field name="foo"/>
                            <field name="bar"/>
                        </tree>`,
                    mockRPC: function (route, args) {
                        if (args.method === "search_read" && args.model === "ir.module.module") {
                            assert.step("studio_module_id");
                            return Promise.resolve([{ id: 42 }]);
                        }
                        if (
                            args.method === "button_immediate_install" &&
                            args.model === "ir.module.module"
                        ) {
                            assert.deepEqual(
                                args.args[0],
                                [42],
                                "Should be the id of studio module returned by the search read"
                            );
                            assert.step("studio_module_install");
                            return true;
                        }
                    },
                });

                patchWithCleanup(browser.location, {
                    reload: function () {
                        assert.step("window_reload");
                    },
                });

                assert.containsN(target, ".o_data_row", 4);
                assert.containsOnce(target, ".o_optional_columns_dropdown_toggle");

                await click(target, ".o_optional_columns_dropdown_toggle");
                assert.containsOnce(target, ".o_optional_columns_dropdown .dropdown-item");
                assert.containsOnce(target, ".o_optional_columns_dropdown .dropdown-item-studio");

                await click(target, ".o_optional_columns_dropdown .dropdown-item-studio");
                await nextTick();
                assert.containsOnce(target, ".modal-studio");

                await click(target, ".modal .o_install_studio");
                assert.equal(browser.localStorage.getItem("openStudioOnReload"), "main");
                assert.verifySteps(["studio_module_id", "studio_module_install", "window_reload"]);
            }
        );

        QUnit.test(
            "add custom field button not shown to non-system users (with opt. col.)",
            async function (assert) {
                assert.expect(3);

                patchWithCleanup(session, { is_system: false });

                await makeView({
                    serverData,
                    type: "list",
                    resModel: "foo",
                    config,
                    arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar" optional="hide"/>
                    </tree>`,
                });

                assert.containsOnce(target, ".o_optional_columns_dropdown_toggle");
                await click(target, ".o_optional_columns_dropdown_toggle");
                assert.containsOnce(target, ".o_optional_columns_dropdown .dropdown-item");
                assert.containsNone(target, ".o_optional_columns_dropdown .dropdown-item-studio");
            }
        );

        QUnit.test(
            "add custom field button not shown to non-system users (wo opt. col.)",
            async function (assert) {
                assert.expect(1);
                patchWithCleanup(session, { is_system: false });

                await makeView({
                    serverData,
                    type: "list",
                    resModel: "foo",
                    config,
                    arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
                });

                assert.containsNone(target, ".o_optional_columns_dropdown_toggle");
            }
        );

        QUnit.test(
            "add custom field button not shown with invalid action",
            async function (assert) {
                assert.expect(1);
                patchWithCleanup(session, { is_system: false });
                config.actionId = null;
                await makeView({
                    serverData,
                    type: "list",
                    resModel: "foo",
                    config,
                    arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
                });

                assert.containsNone(target, ".o_optional_columns_dropdown_toggle");
            }
        );

        QUnit.test("x2many should not be editable", async (assert) => {
            patchWithCleanup(session, { is_system: true });
            serverData.models.bar = {
                fields: {},
                records: [],
            };
            serverData.models.foo.fields.o2m = { type: "one2many", relation: "bar", string: "" };
            await makeView({
                serverData,
                type: "form",
                resModel: "foo",
                arch: `
                <form>
                    <notebook>
                        <page>
                            <field name="o2m">
                                <tree>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </page>
                        <page><div class="test_empty_page" /></page>
                    </notebook>
                </form>`,
            });
            assert.containsNone(target, ".o_optional_columns_dropdown_toggle");
            await click(target.querySelectorAll(".nav-link")[1]);
            assert.containsNone(target, ".o_field_widget");
            await click(target.querySelectorAll(".nav-link")[0]);
            assert.containsOnce(target, ".o_field_widget");
            assert.containsNone(target, ".o_optional_columns_dropdown_toggle");
        });

        QUnit.test("upsell studio feature is not polluted by another view", async (assert) => {
            patchWithCleanup(session, { is_system: true });

            const serviceRegistry = registry.category("services");
            serviceRegistry.add("home_menu", homeMenuService);
            serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);

            serverData = getActionManagerServerData();

            serverData.views = {
                "partner,false,list": `<tree><field name="display_name" /> <field name="name" optional="1" /></tree>`,
                "partner,false,search": `<search />`,
            };

            const wc = await createEnterpriseWebClient({ serverData });
            await doAction(wc, {
                xml_id: "editable",
                id: 999,
                type: "ir.actions.act_window",
                views: [[false, "list"]],
                res_model: "partner",
            });

            await click(target, ".o_optional_columns_dropdown_toggle");
            assert.containsN(target, ".o_optional_columns_dropdown .dropdown-item", 2);
            assert.containsOnce(target, ".o_optional_columns_dropdown .dropdown-item-studio");

            await doAction(wc, {
                id: 99,
                xml_id: "in_dialog",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
                res_model: "partner",
                target: "new",
            });

            await click(target, ".modal .o_optional_columns_dropdown_toggle");
            assert.containsOnce(target, ".modal .dropdown-item");
            assert.containsNone(target, ".modal .dropdown-item-studio");
            await click(target, ".modal-header .btn-close");
            assert.containsNone(target, ".modal");

            await click(target, ".o_optional_columns_dropdown_toggle");
            assert.containsNone(target, ".o_optional_columns_dropdown_toggle o-dropdown-menu");
            await click(target, ".o_optional_columns_dropdown_toggle");

            assert.containsN(target, ".o_optional_columns_dropdown .dropdown-item", 2);
            assert.containsOnce(target, ".o_optional_columns_dropdown .dropdown-item-studio");
        });
    }
);
