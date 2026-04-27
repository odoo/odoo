/** @odoo-module */
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { actionService } from "@web/webclient/actions/action_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { viewService } from "@web/views/view_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

import { NewModelItem } from "@web_studio/client_action/editor/new_model_item/new_model_item";

import { getFixture, mount, click, editInput, nextTick } from "@web/../tests/helpers/utils";
import { registerStudioDependencies } from "./helpers";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

QUnit.module("Studio Navbar > New Model", (hooks) => {
    const serviceRegistry = registry.category("services");

    class Parent extends Component {
        static components = { MainComponentsContainer, NewModelItem };
        static template = xml`<MainComponentsContainer /><NewModelItem />`;
        static props = ["*"];
    }

    async function createNewModelIem(config = {}) {
        const env = await makeTestEnv({ ...config, serverData });
        await mount(Parent, target, { env });
        await env.services.menu.setCurrentMenu(1);
        return nextTick();
    }

    let target;
    let serverData;
    hooks.beforeEach(() => {
        target = getFixture();
        registerStudioDependencies();

        serviceRegistry.add("action", actionService);
        serviceRegistry.add("view", viewService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("menu", menuService);
        serviceRegistry.add("hotkey", hotkeyService);
        const menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App0", appID: 1 },
        };
        serverData = { menus };
    });

    QUnit.test("Add New Model", async function (assert) {
        assert.expect(10);

        serverData.actions = {
            99999: {
                type: "ir.actions.act_window",
                xmlid: "test.99",
                views: [[false, "form"]],
                name: "test",
                res_model: "p",
            },
        };

        serverData.views = {
            "p,false,form": "<form/>",
        };

        serverData.models = {
            p: { fields: {}, records: [] },
        };

        await createNewModelIem({
            mockRPC: (route, args) => {
                if (route === "/web_studio/create_new_menu") {
                    assert.strictEqual(args.menu_name, "ABCD", "Model name should be ABCD.");
                    assert.deepEqual(args.model_options, [
                        "use_sequence",
                        "use_mail",
                        "use_active",
                    ]);
                    return { action_id: 99999 };
                }
                if (route === "/web/action/load") {
                    assert.step(`loadAction ${args.action_id}`);
                }
            },
        });

        assert.containsNone(
            target,
            ".o_web_studio_new_model_modal",
            "there should not be any modal in the dom"
        );
        assert.containsOnce(
            target,
            ".o_web_create_new_model",
            "there should be an add new model link"
        );

        await click(target, ".o_web_create_new_model");
        assert.containsOnce(
            target,
            ".o_web_studio_new_model_modal",
            "there should be a modal in the dom"
        );
        const modal = target.querySelector(".modal");
        assert.containsOnce(
            modal,
            'input[name="model_name"]',
            "there should be an input for the name in the dialog"
        );

        await editInput(modal, 'input[name="model_name"]', "ABCD");
        await click(modal.querySelector("footer .btn-primary"));
        const configuratorModal = target.querySelector(".o_web_studio_model_configurator");
        assert.containsOnce(
            configuratorModal,
            'input[name="use_partner"]',
            "the ModelConfigurator should show the available model options"
        );

        await click(configuratorModal, ".o_web_studio_model_configurator_next");
        assert.containsNone(
            target,
            ".o_web_studio_model_configurator",
            "the ModelConfigurator should be gone"
        );
        await nextTick();
        assert.verifySteps(["loadAction 99999"]);
    });
});
