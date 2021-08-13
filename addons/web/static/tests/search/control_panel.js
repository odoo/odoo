/** @odoo-module **/

import { actionService } from "@web/webclient/actions/action_service";
import { click } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { getFixture } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { notificationService } from "@web/core/notifications/notification_service";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

const { mount } = owl;

/**
 * @param {MakeViewParams} params
 * @returns {owl.Component}
 */
export async function makeControlPanel(params = {}) {
    const serverData = params.serverData;
    const mockRPC = params.mockRPC;
    const props = Object.assign({}, params);
    delete props.serverData;
    delete props.mockRPC;

    const env = await makeTestEnv({ serverData, mockRPC });
    const target = getFixture();

    const controlPanel = await mount(ControlPanel, { env, props, target });

    registerCleanup(() => controlPanel.destroy());

    return controlPanel;
}

QUnit.module("ControlPanel", {
    async beforeEach() {
        serviceRegistry.add("action", actionService);
        serviceRegistry.add("notification", notificationService);
    },
});

QUnit.test("simple rendering", async (assert) => {
    const controlPanel = await makeControlPanel({
        display: {
            "top-right": false,
        },
    });
    assert.containsOnce(controlPanel, ".o_cp_top");
    assert.containsOnce(controlPanel, ".o_cp_top_left");
    assert.containsNone(controlPanel, ".o_cp_top_right");
    assert.containsOnce(controlPanel, ".o_cp_bottom");
    assert.containsOnce(controlPanel, ".o_cp_bottom_left");
    assert.containsOnce(controlPanel, ".o_cp_bottom_right");

    assert.containsNone(controlPanel, ".o_cp_switch_buttons");

    assert.containsOnce(controlPanel, ".breadcrumb");
    assert.containsOnce(controlPanel, ".breadcrumb li.breadcrumb-item");
    assert.strictEqual(controlPanel.el.querySelector("li.breadcrumb-item").innerText, "Unnamed");
});

QUnit.test("breadcrumbs prop", async (assert) => {
    const controlPanel = await makeControlPanel({
        breadcrumbs: [{ jsId: "controller_7", name: "Previous" }],
        displayName: "Current",
    });

    assert.containsN(controlPanel, ".breadcrumb li.breadcrumb-item", 2);
    const breadcrumbItems = controlPanel.el.querySelectorAll("li.breadcrumb-item");
    assert.strictEqual(breadcrumbItems[0].innerText, "Previous");
    assert.hasClass(breadcrumbItems[1], "active");
    assert.strictEqual(breadcrumbItems[1].innerText, "Current");

    controlPanel.env.services.action.restore = (jsId) => {
        assert.step(jsId);
    };

    await click(breadcrumbItems[0]);
    assert.verifySteps(["controller_7"]);
});

QUnit.test("viewSwitcherEntries prop", async (assert) => {
    const controlPanel = await makeControlPanel({
        viewSwitcherEntries: [
            { type: "list", active: true, icon: "fa-list-ul", name: "List" },
            { type: "kanban", icon: "fa-th-large", name: "Kanban" },
        ],
    });

    assert.containsOnce(controlPanel, ".o_cp_switch_buttons");
    assert.containsN(controlPanel, ".o_switch_view", 2);
    const views = controlPanel.el.querySelectorAll(".o_switch_view");

    assert.strictEqual(views[0].getAttribute("data-tooltip"), "List");
    assert.hasClass(views[0], "active");
    assert.strictEqual(views[1].getAttribute("data-tooltip"), "Kanban");
    assert.hasClass(views[1], "fa-th-large");

    controlPanel.env.services.action.switchView = (viewType) => {
        assert.step(viewType);
    };

    await click(views[1]);
    assert.verifySteps(["kanban"]);
});
