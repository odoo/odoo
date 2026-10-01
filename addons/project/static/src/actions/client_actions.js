import { usePlugin } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export function showTemplateUndoNotification(
    {
        model,
        recordId,
        message,
        undoMethod = "action_undo_convert_to_template",
        actionType = "success",
        undoCallback,
    }
) {
    const action = usePlugin(ActionPlugin);
    const notification = usePlugin(NotificationPlugin);
    const orm = usePlugin(ORM);

    const undoNotification = notification.add(_t(message), {
        type: actionType,
        buttons: [
            {
                name: _t("Undo"),
                icon: "undo",
                onClick: async () => {
                    const res = await orm.call(model, undoMethod, [recordId]);
                    if (undoCallback) {
                        await orm.call(model, undoCallback.method, undoCallback.args);
                    }
                    if (res && undoMethod !== "unlink") {
                        action.doAction(res);
                    } else if (undoMethod === "unlink") {
                        // Taking out the controller to be restored after unlinking the record
                        const restoreController =
                            action.currentController.config.breadcrumbs?.at(-2);
                        await restoreController?.onSelected();
                        const postAction = undoCallback?.post_action;
                        if (postAction) {
                            action.doAction(postAction);
                        }
                    }
                    undoNotification();
                },
            },
        ],
    });
}

export function showTemplateUndoConfirmationDialog(
    {
        model,
        recordId,
        bodyMessage,
        confirmLabel,
        undoMethod = "action_undo_convert_to_template",
        confirmationCallback,
    }
) {
    const action = usePlugin(ActionPlugin);
    const dialog = usePlugin(DialogPlugin);
    const orm = usePlugin(ORM);

    dialog.add(ConfirmationDialog, {
        body: bodyMessage,
        confirmLabel: confirmLabel,
        confirm: async () => {
            const actionDescr = await orm.call(model, undoMethod, [recordId]);
            await action.doAction(actionDescr);
            if (confirmationCallback) {
                await orm.call(
                    model,
                    confirmationCallback.method,
                    confirmationCallback.args
                );
            }
        },
        cancel: () => {},
    });
}

export async function showTemplateView({ recordId }) {
    const action = usePlugin(ActionPlugin);
    const orm = usePlugin(ORM);

    const actionDescr = await orm.call(
        "project.project",
        "action_create_template_from_project",
        [recordId]
    );
    const templateId = actionDescr.params.project_id;
    const currentView = action.currentController.view.type;
    if (currentView === "form") {
        await action.doAction({
            type: "ir.actions.act_window",
            res_model: "project.project",
            views: [[false, "form"]],
            res_id: templateId,
        });
    } else {
        await action.doAction("project.act_project_project_2_project_task_all", {
            viewType: currentView,
            stackPosition: "replaceCurrentAction",
            additionalContext: { active_id: templateId },
        });
    }
    await action.doAction(actionDescr);
}
export async function showProjectForm({ model, recordId }) {
    const action = usePlugin(ActionPlugin);
    await action.doAction({
        type: "ir.actions.act_window",
        res_model: model,
        views: [[false, "form"]],
        res_id: recordId,
    });
}

// Task → Template Notification
registry.category("actions").add("project_show_template_notification", (action) => {
    const params = action.params || {};
    showTemplateUndoNotification({
        model: "project.task",
        recordId: params.task_id,
        message: _t("Task converted to template"),
    });
    return params.next;
});

// Task → Template Undo Confirmation Dialog
registry
    .category("actions")
    .add("project_show_template_undo_confirmation_dialog", (action) => {
        const params = action.params || {};
        showTemplateUndoConfirmationDialog({
            model: "project.task",
            recordId: params.task_id,
            bodyMessage: _t(
                "This task is currently a template. Would you like to convert it back into a regular task?"
            ),
            confirmLabel: _t("Convert to Task"),
        });
        return params.next;
    });

// Project → Template Create Redirection
registry.category("actions").add("project_to_template_redirection_action", (action) => {
    const params = action.params || {};
    return showTemplateView({ recordId: params.project_id });
});

// Project → Template Notification
registry.category("actions").add("project_template_show_notification", (action) => {
    const params = action.params || {};
    showTemplateUndoNotification({
        model: "project.project",
        recordId: params.project_id,
        message: params.message || _t("Project converted to template."),
        undoMethod: params.undo_method,
        undoCallback: params.callback_data || null,
    });
    return params.next;
});

// Project → Template Undo Confirmation Dialog
registry
    .category("actions")
    .add("project_template_show_undo_confirmation_dialog", (action) => {
        const params = action.params || {};
        showTemplateUndoConfirmationDialog({
            model: "project.project",
            recordId: params.project_id,
            bodyMessage: params.message,
            confirmLabel: _t("Revert to Project"),
            confirmationCallback: params.callback_data || null,
        });
        return params.next;
    });

// Top Menu → Project Form  Make Breadcrumbs
registry.category("actions").add("project_top_menu_overview", (action) => {
    const params = action || {};
    console.log(params);
    showProjectForm({
        model: "project.project",
        recordId: action.res_id,
    });
    return params.next;
});
