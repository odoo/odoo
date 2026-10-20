import { beforeEach, expect, test } from "@odoo/hoot";
import { drag, queryAllTexts } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWebClient,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";

class Partner extends models.Model {
    name = fields.Char();

    _records = [{ id: 1, name: "First partner" }];
    _views = {
        form: `<form><field name="name"/></form>`,
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };
}

defineModels([Partner]);

const HUB_ID = 1;
const ITEMS = [
    {
        id: 1,
        display_name: "Form",
        action_id: false,
        python_method: "action_open_form",
        context: "{'from_item': 'form', 'record_id': active_id}",
    },
    {
        id: 2,
        display_name: "Partners",
        action_id: [10, "Partners"],
        python_method: false,
        context: "{'from_item': 'partners', 'record_id': active_id}",
    },
    {
        id: 3,
        display_name: "Hidden",
        action_id: false,
        python_method: "action_open_hidden",
        context: "{}",
    },
];

/** the hub of an action opening ``activeItemId`` for the partner 1, as sent by the server */
function hubInfo(activeItemId) {
    return {
        id: HUB_ID,
        res_model: "partner",
        res_id: 1,
        active_item_id: activeItemId,
        invisible_item_ids: [3],
    };
}

/** the action of a python method item, as returned by call_button */
function formAction(activeItemId) {
    return {
        type: "ir.actions.act_window",
        res_model: "partner",
        res_id: 1,
        views: [[false, "form"]],
        hub: hubInfo(activeItemId),
    };
}

function setHubSetting(setting) {
    user.updateUserSettings("hub_config_ids", { [`${HUB_ID},1`]: setting });
}

beforeEach(() => {
    defineActions([
        {
            id: 10,
            name: "Partners",
            res_model: "partner",
            views: [[false, "list"]],
            hub: hubInfo(2),
        },
    ]);
    onRpc("lazy_session_info", () => ({
        hubs: { partner: { id: HUB_ID, item_ids: ITEMS } },
    }));
    onRpc("has_group", () => true);
    onRpc("action_open_form", () => formAction(1));
    onRpc("action_open_hidden", () => formAction(3));
    onRpc("set_hub_setting", ({ args }) => {
        expect.step(["set_hub_setting", args[3]]);
        return true;
    });
    user.updateUserSettings("id", 1);
});

test.tags("desktop");
// the tabs are the pinned items, in their order, with the opened one active
test("tabs show the pinned items", async () => {
    setHubSetting({ pinned_item_ids: [2, 1], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    expect(queryAllTexts(".o_hub_tab")).toEqual(["Partners", "Form"]);
    expect(".o_hub_tab .nav-link.active").toHaveText("Form");
});

test.tags("desktop");
// clicking a tab opens its item for the hub's record, in place of the current action
test("clicking a tab opens its item", async () => {
    setHubSetting({ pinned_item_ids: [1, 2], show_tabs: true });
    onRpc("/web/action/load", async (request) => {
        const { params } = await request.json();
        expect.step(["load", params.action_id, params.context.active_id]);
    });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains(".o_hub_tab .nav-link:contains(Partners)").click();
    expect.verifySteps([["load", 10, 1]]);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_hub_tab .nav-link.active").toHaveText("Partners");
    expect(".o_breadcrumb .breadcrumb-item").toHaveCount(0);
});

test.tags("desktop");
// the context of an item is evaluated for the hub's record, for actions and methods
test("items open with their context", async () => {
    setHubSetting({ pinned_item_ids: [1, 2], show_tabs: true });
    onRpc("/web/action/load", async (request) => {
        const { context } = (await request.json()).params;
        expect.step(["load", context.from_item, context.record_id]);
    });
    onRpc("action_open_form", ({ kwargs }) => {
        expect.step(["call", kwargs.context.from_item, kwargs.context.record_id]);
    });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains(".o_hub_tab .nav-link:contains(Partners)").click();
    expect.verifySteps([["load", "partners", 1]]);
    await contains(".o_hub_tab .nav-link:contains(Form)").click();
    expect.verifySteps([["call", "form", 1]]);
});

test.tags("desktop");
// showing the tabs the first time starts from the default setting of the server
test("first show of the tabs uses the default setting", async () => {
    onRpc("get_default_hub_setting", () => ({ pinned_item_ids: [2] }));
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    expect(".o_hub_tabs").toHaveCount(0);
    await contains("button[name=hub_tabs]").click();
    expect.verifySteps([["set_hub_setting", { show_tabs: true, pinned_item_ids: [2] }]]);
    expect(queryAllTexts(".o_hub_tab")).toEqual(["Partners"]);
});

test.tags("desktop");
// showing the tabs with no item pinned pins the first item
test("showing the tabs with no pin pins the first item", async () => {
    onRpc("get_default_hub_setting", () => ({}));
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains("button[name=hub_tabs]").click();
    expect.verifySteps([["set_hub_setting", { show_tabs: true, pinned_item_ids: [1] }]]);
    expect(queryAllTexts(".o_hub_tab")).toEqual(["Form"]);
});

test.tags("desktop");
// hiding the tabs only saves their visibility
test("hiding the tabs", async () => {
    setHubSetting({ pinned_item_ids: [1], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains("button[name=hub_tabs]").click();
    expect.verifySteps([["set_hub_setting", { show_tabs: false }]]);
    await runAllTimers(); // the tabs fade out
    expect(".o_hub_tabs").toHaveCount(0);
});

test.tags("desktop");
// selecting an item in the dropdown pins it last, selecting it again unpins it
test("pin and unpin items from the dropdown", async () => {
    setHubSetting({ pinned_item_ids: [1], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains(".o_hub_tabs_toggler").click();
    await contains(".o_hub_tabs_dropdown_menu .o-dropdown-item:contains(Partners)").click();
    expect.verifySteps([["set_hub_setting", { pinned_item_ids: [1, 2] }]]);
    expect(queryAllTexts(".o_hub_tab")).toEqual(["Form", "Partners"]);
    await contains(".o_hub_tabs_dropdown_menu .o-dropdown-item:contains(Partners)").click();
    expect.verifySteps([["set_hub_setting", { pinned_item_ids: [1] }]]);
    expect(queryAllTexts(".o_hub_tab")).toEqual(["Form"]);
});

test.tags("desktop");
// a save is only sent once the previous one is done, so the last one wins
test("saves of the pinned items are sent one after the other", async () => {
    setHubSetting({ pinned_item_ids: [1], show_tabs: true });
    const firstSave = Promise.withResolvers();
    let saveCount = 0;
    onRpc("set_hub_setting", async ({ args }) => {
        expect.step(["set_hub_setting", args[3]]);
        if (++saveCount === 1) {
            await firstSave.promise;
        }
        return true;
    });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains(".o_hub_tabs_toggler").click();
    await contains(".o_hub_tabs_dropdown_menu .o-dropdown-item:contains(Partners)").click();
    await contains(".o_hub_tabs_dropdown_menu .o-dropdown-item:contains(Partners)").click();
    expect.verifySteps([["set_hub_setting", { pinned_item_ids: [1, 2] }]]);
    firstSave.resolve();
    await animationFrame();
    expect.verifySteps([["set_hub_setting", { pinned_item_ids: [1] }]]);
});

test.tags("desktop");
// dragging a tab after another one saves the new order of the pinned items
test("reorder tabs with drag and drop", async () => {
    setHubSetting({ pinned_item_ids: [1, 2], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    // the drag starts after a delay, and a move within the tab: only then
    // does entering another tab move the dragged one
    const { drop, moveTo } = await drag(".o_hub_tab:contains(Form)");
    await advanceTime(200);
    await moveTo(".o_hub_tab:contains(Form)", { position: "right" });
    await moveTo(".o_hub_tab:contains(Partners)");
    await drop();
    await animationFrame();
    expect.verifySteps([["set_hub_setting", { pinned_item_ids: [2, 1] }]]);
    expect(queryAllTexts(".o_hub_tab")).toEqual(["Partners", "Form"]);
});

test.tags("desktop");
// the items hidden for the record are not listed, unless opened
test("items hidden for the record", async () => {
    setHubSetting({ pinned_item_ids: [1], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    await contains(".o_hub_tabs_toggler").click();
    expect(queryAllTexts(".o_hub_tabs_dropdown_menu .o-dropdown-item")).toEqual([
        "Form",
        "Partners",
    ]);
    await getService("action").doAction(formAction(3));
    await contains(".o_hub_tabs_toggler").click();
    expect(queryAllTexts(".o_hub_tabs_dropdown_menu .o-dropdown-item")).toEqual([
        "Form",
        "Partners",
        "Hidden",
    ]);
});

test.tags("desktop");
// an action opened in a dialog doesn't display its hub
test("no hub in a dialog", async () => {
    setHubSetting({ pinned_item_ids: [1], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction({ ...formAction(1), target: "new" });
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".o_hub_tabs").toHaveCount(0);
    expect("button[name=hub_tabs]").toHaveCount(0);
});

test.tags("desktop");
// hub_default opens the first item pinned by the user
test("hub_default opens the first pinned item", async () => {
    setHubSetting({ pinned_item_ids: [2, 1], show_tabs: true });
    await mountWebClient();
    await getService("action").doAction("hub_default", {
        additionalContext: { active_model: "partner", active_id: 1 },
    });
    expect(".o_list_view").toHaveCount(1);
    expect(".o_hub_tab .nav-link.active").toHaveText("Partners");
});

test.tags("desktop");
// hub_default opens the first item of the hub when the user pinned none
test("hub_default opens the first item without pin", async () => {
    await mountWebClient();
    await getService("action").doAction("hub_default", {
        additionalContext: { active_model: "partner", active_id: 1 },
    });
    expect(".o_form_view").toHaveCount(1);
});

// on small screens, the items are listed in a dropdown of the control panel instead of tabs
test.tags("mobile");
test("mobile dropdown lists the items", async () => {
    await mountWebClient();
    await getService("action").doAction(formAction(1));
    expect(".o_hub_tabs").toHaveCount(0);
    expect("button[name=hub_tabs]").toHaveCount(0);
    await contains(".o_control_panel button[data-tooltip='View related documents']").click();
    expect(queryAllTexts(".o_bottom_sheet .o_hub_items_mobile_dropdown .o-dropdown-item")).toEqual([
        "Form",
        "Partners",
    ]);
    expect(".o_bottom_sheet .o_hub_items_mobile_dropdown .o-dropdown-item.selected").toHaveText(
        "Form"
    );
    await contains(
        ".o_bottom_sheet .o_hub_items_mobile_dropdown .o-dropdown-item:contains(Partners)"
    ).click();
    expect(".o_list_view").toHaveCount(1);
});
