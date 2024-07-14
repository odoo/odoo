/** @odoo-module */
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { menuService } from "@web/webclient/menus/menu_service";
import { MainComponentsContainer } from "@web/core/main_components_container";

import { AppMenuEditor } from "@web_studio/client_action/editor/app_menu_editor/app_menu_editor";

import {
    dragAndDrop,
    getFixture,
    mount,
    click,
    editInput,
    nextTick,
} from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

import { setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("Studio Navbar > AppMenuEditor", (hooks) => {
    const serviceRegistry = registry.category("services");

    class Parent extends Component {
        static components = { MainComponentsContainer, AppMenuEditor };
        static template = xml`<MainComponentsContainer /><AppMenuEditor env="env"/>`;
    }

    async function createAppMenuEditor(config = {}) {
        const env = await makeTestEnv({ ...config, serverData });
        await mount(Parent, target, { env });
        await env.services.menu.setCurrentMenu(2);
        return nextTick();
    }

    let target;
    let serverData;
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {};
        serverData.models = {
            "ir.ui.menu": {
                fields: {},
                records: [
                    {
                        id: 1,
                        name: "Menu 1",
                    },
                    {
                        id: 2,
                        name: "App2",
                    },
                    {
                        id: 21,
                        name: "Submenu 1",
                    },
                    {
                        id: 22,
                        name: "Submenu 2",
                    },
                ],
            },
        };
        serverData.menus = {
            root: { id: "root", children: [1, 2], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App0", appID: 1 },
            2: { id: 2, children: [21, 22], name: "App2", appID: 2 },
            21: { id: 21, children: [], name: "Menu21", appID: 2 },
            22: { id: 22, children: [221], name: "Menu22", appID: 2 },
            221: { id: 221, children: [], name: "Menu221", appID: 2 },
        };

        serverData.views = {
            "ir.ui.menu,false,form": `<form>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        };

        setupViewRegistries();
        serviceRegistry.add("menu", menuService);
    });

    QUnit.test("edit menu behavior", async function (assert) {
        assert.expect(3);

        await createAppMenuEditor();
        assert.containsNone(target, ".o-web-studio-appmenu-editor");
        assert.containsOnce(target, ".o_web_edit_menu", "there should be an edit menu link");

        // open the dialog to edit the menu
        await click(target, ".o_web_edit_menu");
        assert.containsOnce(target, ".o-web-studio-appmenu-editor");
    });

    QUnit.test("edit menu dialog rendering", async (assert) => {
        await createAppMenuEditor();
        await click(target, ".o_web_edit_menu");

        const modal = target.querySelector(".modal");
        assert.containsOnce(target, "ul.oe_menu_editor", "there should be the list of menus");
        assert.containsOnce(target, "ul.oe_menu_editor > li", "there should be only one main menu");
        assert.strictEqual(
            target.querySelector("ul.oe_menu_editor > li").dataset.itemId,
            "2",
            "the main menu should have the menu-id 2"
        );
        assert.containsOnce(
            target,
            "ul.oe_menu_editor > li > div button.o-web-studio-interactive-list-edit-item",
            "there should be a button to edit the menu"
        );
        assert.containsOnce(
            target,
            "ul.oe_menu_editor > li > div button.o-web-studio-interactive-list-edit-item",
            "there should be a button to remove the menu"
        );
        assert.containsN(
            target,
            "ul.oe_menu_editor > li > ul > li",
            2,
            "there should be two submenus"
        );
        assert.containsOnce(modal, ".js_add_menu", "there should be a link to add new menu");
        assert.hasClass(
            target.querySelector(".o-web-studio-interactive-list-remove-item"),
            "disabled"
        );
    });

    QUnit.test("edit menu dialog: create menu", async function (assert) {
        await createAppMenuEditor({
            mockRPC: (route, args) => {
                assert.step(route);
                if (route === "/web_studio/create_new_menu") {
                    assert.strictEqual(args.menu_name, "AA");
                    assert.strictEqual(args.model_choice, "new");
                    assert.deepEqual(args.model_options, [
                        "use_sequence",
                        "use_mail",
                        "use_active",
                    ]);
                    assert.strictEqual(args.parent_menu_id, 2);
                    return {};
                }
            },
        });

        assert.verifySteps(["/web/webclient/load_menus"]);
        await click(target, ".o_web_edit_menu");
        const modal = target.querySelector(".modal");

        // open the dialog to create a new menu
        await click(modal, ".js_add_menu");
        await nextTick();
        assert.containsOnce(target, ".o_web_studio_add_menu_modal");
        assert.containsOnce(target, `.o_web_studio_add_menu_modal input[name="menuName"]`);

        await click(
            target,
            '.o_web_studio_add_menu_modal .o_web_studio_menu_creator_model_choice input[value="new"]'
        );
        assert.containsNone(
            target,
            ".o_web_studio_add_menu_modal .o_record_selector",
            "there should be no visible many2one for the model in the dialog"
        );

        await editInput(target, "input[name='menuName']", "new_model");
        await click(target, ".o_web_studio_add_menu_modal .btn-primary");
        assert.containsOnce(
            target,
            '.o_web_studio_model_configurator input[name="use_partner"]',
            "the ModelConfigurator should show the available model options"
        );

        await click(
            target,
            ".o_web_studio_model_configurator .o_web_studio_model_configurator_previous"
        );
        assert.containsNone(
            target,
            ".o_web_studio_model_configurator",
            "the ModelConfigurator should be gone"
        );

        await click(
            target,
            '.o_web_studio_add_menu_modal .o_web_studio_menu_creator_model_choice [value="existing"]'
        );
        assert.containsOnce(target, ".o_web_studio_add_menu_modal .o_record_selector");

        // add menu and close the modal
        await editInput(target, '.o_web_studio_add_menu_modal input[name="menuName"]', "AA");
        await click(
            target,
            '.o_web_studio_add_menu_modal .o_web_studio_menu_creator_model_choice [value="new"]'
        );
        await click(target, ".o_web_studio_add_menu_modal .btn-primary");

        await click(target, ".o_web_studio_model_configurator .btn-primary");
        assert.verifySteps(["/web_studio/create_new_menu", "/web/webclient/load_menus"]);
    });

    QUnit.test("drag/drop to reorganize menus", async (assert) => {
        await createAppMenuEditor({
            mockRPC: (route, args) => {
                assert.step(route);
                if (route === "/web/dataset/call_kw/ir.ui.menu/customize") {
                    assert.deepEqual(args.kwargs.to_delete, []);
                    assert.deepEqual(args.kwargs.to_move, {
                        21: {
                            sequence: 2,
                        },
                        22: {
                            sequence: 3,
                        },
                        221: {
                            parent_menu_id: 2,
                            sequence: 1,
                        },
                    });

                    return true;
                }
            },
        });
        assert.verifySteps(["/web/webclient/load_menus"]);

        await click(target, ".o_web_edit_menu");

        // Avoid flickering of the modal content always centered
        const modalDialog = target.querySelector(".modal .modal-dialog");
        modalDialog.classList.remove("modal-dialog-centered");

        // move submenu above root menu
        const fromSelector = "li[data-item-id='221'] .o-draggable-handle";
        const fromNode = target.querySelector(fromSelector);
        const fromRect = fromNode.getBoundingClientRect();

        const containerNode = target.querySelector(".oe_menu_editor");
        const containerNodeRect = containerNode.getBoundingClientRect();

        const position = {
            x: 0,
            y: fromRect.top - containerNodeRect.top + fromRect.height / 2,
        };

        await dragAndDrop(fromNode, containerNode, position);
        await dragAndDrop(fromSelector, "li[data-item-id='21'] .o-draggable-handle");

        await click(target, ".o-web-studio-appmenu-editor footer .btn-primary");
        assert.verifySteps([
            "/web/dataset/call_kw/ir.ui.menu/customize",
            "/web/webclient/load_menus",
        ]);
    });

    QUnit.test("edit/delete menus", async (assert) => {
        await createAppMenuEditor({
            mockRPC: (route, args) => {
                assert.step(route);
                if (route === "/web/dataset/call_kw/ir.ui.menu/customize") {
                    assert.deepEqual(args.kwargs.to_delete, [221]);
                    return true;
                }
            },
        });
        assert.verifySteps(["/web/webclient/load_menus"]);
        await click(target, ".o_web_edit_menu");
        assert.containsOnce(target, ".o_dialog");
        // open the dialog to edit the menu
        await click(target.querySelector(".o-web-studio-interactive-list-edit-item"));
        assert.containsN(target, ".o_dialog", 2);
        assert.containsOnce(target, ".o_dialog .o_form_view");

        assert.verifySteps([
            "/web/dataset/call_kw/ir.ui.menu/get_views",
            "/web/dataset/call_kw/ir.ui.menu/web_read",
        ]);

        assert.strictEqual(
            target.querySelector('.o_dialog .o_form_view .o_field_widget[name="name"] input').value,
            "App2",
            "the edited menu should be App2"
        );
        await click(target, ".o_form_button_save");
        assert.containsOnce(target, ".o_dialog");
        assert.verifySteps(["/web/webclient/load_menus"]);

        // delete the last menu
        assert.containsN(target, ".o-web-studio-interactive-list-remove-item", 4);
        await click(target.querySelectorAll(".o-web-studio-interactive-list-remove-item")[3]);
        assert.containsNone(
            target,
            "ul.oe_menu_editor > li > ul > li > li",
            "there should be no submenu after deletion"
        );

        await click(target, ".modal footer .btn-primary");
        assert.verifySteps([
            "/web/dataset/call_kw/ir.ui.menu/customize",
            "/web/webclient/load_menus",
        ]);
    });
});
