/** @odoo-module alias=@web/../tests/search/control_panel default=false */

import { click, getFixture, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { makeWithSearch, setupControlPanelServiceRegistry } from "./helpers";
import { createWebClient, doAction } from "../webclient/helpers";

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

        assert.containsOnce(target, ".o_control_panel_breadcrumbs");
        assert.containsOnce(target, ".o_control_panel_actions");
        assert.containsNone(target, ".o_control_panel_actions > *");
        assert.containsOnce(target, ".o_control_panel_navigation");
        assert.containsNone(target, ".o_control_panel_navigation > *");

        assert.containsNone(target, ".o_cp_switch_buttons");

        assert.containsOnce(target, ".o_breadcrumb");
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

        const breadcrumbsSelector = ".o_breadcrumb li.breadcrumb-item, .o_breadcrumb .active";
        assert.containsN(target, breadcrumbsSelector, 2);
        const breadcrumbItems = target.querySelectorAll(breadcrumbsSelector);
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

        assert.containsOnce(
            target,
            ".o_control_panel_navigation .d-xl-inline-flex.o_cp_switch_buttons"
        );
        assert.containsN(target, ".o_switch_view", 2);
        const views = target.querySelectorAll(".o_switch_view");

        assert.strictEqual(views[0].getAttribute("data-tooltip"), "List");
        assert.hasClass(views[0], "active");
        assert.containsOnce(views[0], ".oi-view-list");
        assert.strictEqual(views[1].getAttribute("data-tooltip"), "Kanban");
        assert.containsOnce(views[1], ".oi-view-kanban");

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

    QUnit.test("view switcher hotkey cycles through views", async (assert) => {
        serverData.views = {
            "foo,false,search": `<search />`,
            "foo,false,list": `<list></list>`,
            "foo,false,kanban": `<kanban><t t-name="kanban-box"></t></kanban>`,
        };

        const wc = await createWebClient({ serverData });
        await doAction(wc, {
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "kanban"],
            ],
        });

        assert.containsOnce(target, ".o_list_view");
        triggerHotkey("alt+shift+v");
        await nextTick();
        assert.containsOnce(target, ".o_kanban_view");
        triggerHotkey("alt+shift+v");
        await nextTick();
        assert.containsOnce(target, ".o_list_view");
    });
});
