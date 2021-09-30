/** @odoo-module **/

import { click } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { makeWithSearch, setupControlPanelServiceRegistry } from "./helpers";

let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {},
                },
            },
            views: {
                "foo,false,search": `<search/>`,
            },
        };
        setupControlPanelServiceRegistry();
    });

    QUnit.module("ControlPanel");

    QUnit.test("simple rendering", async (assert) => {
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            componentProps: {
                display: {
                    "top-right": false,
                },
            },
            searchMenuTypes: [],
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
        assert.strictEqual(
            controlPanel.el.querySelector("li.breadcrumb-item").innerText,
            "Unnamed"
        );
    });

    QUnit.test("breadcrumbs prop", async (assert) => {
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            config: {
                breadcrumbs: [{ jsId: "controller_7", name: "Previous" }],
                displayName: "Current",
            },
            searchMenuTypes: [],
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
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            config: {
                viewSwitcherEntries: [
                    { type: "list", active: true, icon: "fa-list-ul", name: "List" },
                    { type: "kanban", icon: "fa-th-large", name: "Kanban" },
                ],
            },
            searchMenuTypes: [],
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
});
