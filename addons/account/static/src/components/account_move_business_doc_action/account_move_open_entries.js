/** @odoo-module **/
import { registry } from "@web/core/registry";
export async function openJournalEntries(env, action) {
    let ids = [];
    if (action.params.ids) {
        ids = action.params.ids;
    } else if (action.context.params.resId) {
        ids = [action.context.params.resId];
    } else if (action.context.params.ids) {
        if (Number.isInteger(action.context.params.ids)) {
            ids = [action.context.params.ids];
        } else {
            ids = action.context.params.ids.split(",").map((s) => parseInt(s));
        }
    }

    let actionToDo;
    if (ids.length === 1) {
        actionToDo = await env.services.orm.call(
            "account.move",
            "action_open_business_doc",
            [ids[0]],
            {}
        );
    } else {
        actionToDo = await env.services.action.loadAction("account.action_move_journal_line");
        Object.assign(actionToDo, {
            domain: [["id", "in", ids]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            context: {
                list_view_ref: "account.view_duplicated_moves_tree_js",
            },
        });
        if (action.params.name) {
            actionToDo.display_name = action.params.name;
        }
    }
    return env.services.action.doAction(actionToDo);
}
registry.category("actions").add("action_open_journal_entries", openJournalEntries);
