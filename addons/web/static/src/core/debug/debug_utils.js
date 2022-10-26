/** @odoo-module **/

export function editModelDebug(env, title, model, id) {
    return env.services.action.doAction({
        res_model: model,
        res_id: id,
        name: title,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
        view_mode: "form",
        target: "new",
    });
}
