import { expect, test } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { clickSave, onRpc, mountWithCleanup, getService } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

import { definePlanningModels, PlanningSlot } from "./planning_mock_models";

definePlanningModels();

test("quit form view when save actually deletes", async () => {
    PlanningSlot._records = [
        {
            id: 1,
            name: "shift",
        },
    ];
    PlanningSlot._views = {
        form: `<form js_class="planning_form"><field name="name"/></form>`,
        list: `<list><field name="name"/></list>`,
    };
    // Say a recurrence that repeats for ever.
    // If, on the n'th occurrence, we change the recurrence to have max n-1 occurrences,
    // then the n'th occurrence (which we just saved) is deleted.
    onRpc("web_save", () => []);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Planning",
        res_model: "planning.slot",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    expect(".o_action.o_view_controller.o_list_view").toHaveCount(1);
    await click(".o_data_row .o_data_cell");
    await animationFrame();

    expect(".o_form_view").toHaveCount(1);
    await click("[name='name'] input");
    await edit("new shift");
    await clickSave();

    expect(".o_action.o_view_controller.o_list_view").toHaveCount(1);
});
