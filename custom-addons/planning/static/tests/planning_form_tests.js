/** @odoo-module **/

import {
    click,
    clickSave,
    editInput,
    getFixture,
} from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

let target;
let serverData;

QUnit.module("Planning", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                "planning.slot": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "shift",
                        },
                    ],
                },
            },
        };
    });

    QUnit.module("Form");

    QUnit.test("quit form view when save actually deletes", async function (assert) {
        serverData.views = {
            "planning.slot,false,form": '<form js_class="planning_form"><field name="name"/></form>',
            "planning.slot,false,list": '<tree><field name="name"/></tree>',
            "planning.slot,false,search": '<search></search>',
        };
        const webClient = await createWebClient({
            serverData,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    // Say a recurrence that repeats for ever.
                    // If, on the n'th occurrence, we change the recurrence to have max n-1 occurrences,
                    // then the n'th occurrence (which we just saved) is deleted.
                    return [];
                }
            },
        });
        await doAction(webClient, {
            name: "Planning",
            res_model: "planning.slot",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });

        assert.containsOnce(target, ".o_action.o_view_controller.o_list_view");
        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.containsOnce(target, ".o_form_view");
        await editInput(target, "[name='name'] input", "proute");
        await clickSave(target);

        assert.containsOnce(target, ".o_action.o_view_controller.o_list_view");
    });
});
