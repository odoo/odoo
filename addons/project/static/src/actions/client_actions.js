import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export function showTemplateUndoNotification(
    env,
    {
        model,
        recordId,
        message,
        undoMethod = "unlink",
        actionType = "success",
    }
) {
    const undoNotification = env.services.notification.add(_t(message), {
        type: actionType,
        buttons: [
            {
                name: _t("Undo"),
                icon: "fa-undo",
                onClick: async () => {
                    await env.services.orm.call(model, undoMethod, [recordId])
                    if (undoMethod === "unlink") {
                            env.services.notification.add(_t('Removed from templates'), {
                                type: "success",
                            });
                            env.services.action.doAction({
                                type: "ir.actions.client",
                                tag: "soft_reload",
                            });
                    }
                    undoNotification();
                },
            },
        ],
    });
}

// Project and Task → Template Notification
registry.category("actions").add("project_show_template_notification", (env, action) => {
    const params = action.params || {};
    showTemplateUndoNotification(env, {
        model: params.res_model,
        recordId: params.res_id,
        undoMethod: params.undo_method,
        message: _t("Saved as template"),
    });
    return params.next;
});
