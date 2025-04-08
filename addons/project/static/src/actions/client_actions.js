import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export function displayTemplateNotificationAction(env, action) {
    const params = action.params || {};
    const taskId = params.task_id;
    env.services.notification.add(_t("Task successfully converted to template."), {
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
                },
            },
        ],
    });
    return params.next;
}

registry
    .category("actions")
    .add("project_show_template_notification", displayTemplateNotificationAction);
