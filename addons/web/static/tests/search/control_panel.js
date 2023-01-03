/** @odoo-module **/

import { click, getFixture, nextTick } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { makeWithSearch, setupControlPanelServiceRegistry } from "./helpers";

let target;
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
        target = getFixture();
    });

    QUnit.module("ControlPanel");

    QUnit.test("simple rendering", async (assert) => {
        await makeWithSearch({
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

        assert.containsOnce(target, ".o_cp_top");
        assert.containsOnce(target, ".o_cp_top_left");
        assert.strictEqual(target.querySelector(".o_cp_top_right").innerHTML, "");
        assert.containsOnce(target, ".o_cp_bottom");
        assert.containsOnce(target, ".o_cp_bottom_left");
        assert.containsOnce(target, ".o_cp_bottom_right");

        assert.containsNone(target, ".o_cp_switch_buttons");

        assert.containsOnce(target, ".breadcrumb");
    });

    QUnit.test("breadcrumbs", async (assert) => {
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            config: {
                breadcrumbs: [
                    { jsId: "controller_7", name: "Previous" },
                    { jsId: "controller_9", name: "Current" },
                ],
            },
            searchMenuTypes: [],
        });

        assert.containsN(target, ".breadcrumb li.breadcrumb-item", 2);
        const breadcrumbItems = target.querySelectorAll("li.breadcrumb-item");
        assert.strictEqual(breadcrumbItems[0].innerText, "Previous");
        assert.hasClass(breadcrumbItems[1], "active");
        assert.strictEqual(breadcrumbItems[1].innerText, "Current");

        controlPanel.env.services.action.restore = (jsId) => {
            assert.step(jsId);
        };

        await click(breadcrumbItems[0]);
        assert.verifySteps(["controller_7"]);
    });

    QUnit.test("view switcher", async (assert) => {
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            config: {
                viewSwitcherEntries: [
                    { type: "list", active: true, icon: "oi-view-list", name: "List" },
                    { type: "kanban", icon: "oi-view-kanban", name: "Kanban" },
                ],
            },
            searchMenuTypes: [],
        });

        assert.containsOnce(target, ".o_cp_switch_buttons");
        assert.containsN(target, ".o_switch_view", 2);
        const views = target.querySelectorAll(".o_switch_view");

        assert.strictEqual(views[0].getAttribute("data-tooltip"), "List");
        assert.hasClass(views[0], "active");
        assert.strictEqual(views[1].getAttribute("data-tooltip"), "Kanban");
        assert.hasClass(views[1], "oi-view-kanban");

        controlPanel.env.services.action.switchView = (viewType) => {
            assert.step(viewType);
        };

        await click(views[1]);
        assert.verifySteps(["kanban"]);
    });

    QUnit.test("pager", async (assert) => {
        const pagerProps = {
            offset: 0,
            limit: 10,
            total: 50,
            onUpdate: () => {},
        };

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            config: {
                pagerProps: pagerProps,
            },
            searchMenuTypes: [],
        });
        assert.containsOnce(target, ".o_pager");

        pagerProps.total = 0;
        controlPanel.render();
        await nextTick();
        assert.containsNone(target, ".o_pager");
    });
});
