import { makeContext } from "@web/core/context";

export function openHubItem(actionPlugin, item, {resModel, resId}, options = {}){
    const activeContext = { active_id: resId, active_ids: [resId], active_model: resModel };
    const context = makeContext([item.context], activeContext);
    if (item.action_id) {
       return actionPlugin.doAction(item.action_id[0], {
            additionalContext: {
                ...context,
                ...activeContext,
            },
            ...options
        })
    } else {
        return actionPlugin.doActionButton({
            type: "object",
            name: item.python_method,
            resModel,
            resId,
            context,
            ...options
        });
    }
}
