import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export function displayTemplateNotificationAction(env, action) {
    const params = action.params || {};
    const taskId = params.task_id;
    const removeNotification = env.services.notification.add(_t("Task converted to template"), {
        type: "success",
        buttons: [
            {
                name: "Undo",
                icon: "fa-undo",
                onClick: async () => {
                    const res = await env.services.orm.call(
                        "project.task",
                        "action_undo_convert_to_template",
                        [taskId]
                    );
                    if (res) {
                        env.services.action.doAction(res);
                    }
                    removeNotification();
                },
            },
        ],
    });
    return params.next;
}

registry
    .category("actions")
    .add("project_show_template_notification", displayTemplateNotificationAction);

export function displayTemplateUndoConfirmationDialog(env, action) {
    const params = action.params || {};
    const taskId = params.task_id;
    env.services.dialog.add(ConfirmationDialog, {
        body: _t(
            "This task is already a template. Do you want to convert it back to a regular task?"
        ),
        confirmLabel: _t("Convert to Task"),
        confirm: async () => {
            await env.services.action.doAction(
                await env.services.orm.call("project.task", "action_undo_convert_to_template", [
                    taskId,
                ])
            );
        },
        cancelLabel: _t("Discard"),
        cancel: () => {},
    });
    return params.next;
}

registry
    .category("actions")
    .add("project_show_template_undo_confirmation_dialog", displayTemplateUndoConfirmationDialog);
