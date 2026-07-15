export function editModelDebug(actionService, title, model, id) {
    return actionService.doAction({
        res_model: model,
        res_id: id,
        name: title,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
        view_mode: "form",
        target: "current",
    });
}
