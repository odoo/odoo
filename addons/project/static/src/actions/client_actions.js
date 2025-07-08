import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export async function openFormView(env, { resModel, resId }) {
    await env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: resModel,
        views: [[false, "form"]],
        res_id: resId,
    });
}

export function showTemplateUndoNotification(
    env,
    {
        model,
        recordId,
        message,
        undoMethod = "action_undo_convert_to_template",
        actionType = "success",
        undoCallback,
        templateResId,
        templateResModel,
    }
) {
    const undoNotification = env.services.notification.add(_t(message), {
        type: actionType,
        buttons: [
            {
                name: _t("Undo"),
                icon: "fa-undo",
                onClick: async () => {
                    const res = await env.services.orm.call(model, undoMethod, [recordId]);
                    if (undoCallback) {
                        await env.services.orm.call(model, undoCallback.method, undoCallback.args);
                    }
                    if (res && undoMethod !== "unlink") {
                        env.services.action.doAction(res);
                    } else if (undoMethod === "unlink") {
                        // Taking out the controller to be restored after unlinking the record
                        const restoreController =
                            env.services.action.currentController.config.breadcrumbs?.at(-2);
                        restoreController?.onSelected();
                    }
                    if (undoMethod === 'action_undo_convert_to_template' && res.params.type == 'success') {
                        const { res_id, res_model } = res.params;
                        await openFormView(env, { resModel: res_model, resId: res_id });
                        await env.services.orm.call(templateResModel, "action_archive", [[templateResId]]);
                        env.services.action.currentController.config.breadcrumbs?.pop()
                    }
                    undoNotification();
                },
            },
        ],
    });
}

export function showTemplateUndoConfirmationDialog(
    env,
    {
        model,
        recordId,
        bodyMessage,
        confirmLabel,
        undoMethod = "action_undo_convert_to_template",
        confirmationCallback,
    }
) {
    env.services.dialog.add(ConfirmationDialog, {
        body: bodyMessage,
        confirmLabel: confirmLabel,
        confirm: async () => {
            const action = await env.services.orm.call(model, undoMethod, [recordId]);
            await env.services.action.doAction(action);
            if (action.params.type == 'success') {
                const { res_id, res_model } = action.params;
                await openFormView(env, { resModel: res_model, resId: res_id });
                env.services.action.currentController.config.breadcrumbs?.pop()
            }
            if (confirmationCallback) {
                await env.services.orm.call(
                    model,
                    confirmationCallback.method,
                    confirmationCallback.args
                );
            }
        },
        cancelLabel: _t("Discard"),
        cancel: () => {},
    });
}

export async function showTemplateFormView(
    env,
    { model, recordId, method = "action_create_template_from_project" }
) {
    const action = await env.services.orm.call(model, method, [recordId]);
    await openFormView(env, { resModel: model, resId: action.params.project_id });
    await env.services.action.doAction(action);
}

// Task → Template Notification
registry.category("actions").add("project_show_template_notification", async(env, action) => {
    const params = action.params || {};
    const { template_res_id, template_res_model } = action.params;
    await openFormView(env, { resModel: template_res_model, resId: template_res_id });
    env.services.action.currentController.config.breadcrumbs?.pop()
    showTemplateUndoNotification(env, {
        model: "project.task",
        recordId: params.res_id,
        templateResId: template_res_id,
        templateResModel: template_res_model,
        message: _t("Task converted to template"),
    });
    return params.next;
});

// Task → Template Undo Confirmation Dialog
registry
    .category("actions")
    .add("project_show_template_undo_confirmation_dialog", (env, action) => {
        const params = action.params || {};
        showTemplateUndoConfirmationDialog(env, {
            model: params.res_model,
            recordId: params.res_id,
            bodyMessage: _t(
                "This task is currently a template. Would you like to convert it back into a regular task?"
            ),
            confirmLabel: _t("Convert to Task"),
        });
        return params.next;
    });

// Project → Template Create Redirection
registry.category("actions").add("project_to_template_redirection_action", (env, action) => {
    const params = action.params || {};
    return showTemplateFormView(env, {
        model: "project.project",
        recordId: params.project_id,
    });
});

// Project → Template Notification
registry.category("actions").add("project_template_show_notification", (env, action) => {
    const params = action.params || {};
    showTemplateUndoNotification(env, {
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
    .add("project_template_show_undo_confirmation_dialog", (env, action) => {
        const params = action.params || {};
        showTemplateUndoConfirmationDialog(env, {
            model: "project.project",
            recordId: params.project_id,
            bodyMessage: params.message,
            confirmLabel: _t("Revert to Project"),
            confirmationCallback: params.callback_data || null,
        });
        return params.next;
    });
