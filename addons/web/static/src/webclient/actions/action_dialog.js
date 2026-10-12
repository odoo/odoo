import { t, usePlugin, useProps } from "@odoo/owl";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { Dialog, dialogProps } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";

export class ActionDialog extends Dialog {
    static components = { ...Dialog.components, DebugMenu };
    static template = "web.ActionDialog";
    static propsSchema = {
        ...dialogProps,
        // ActionDialog renders `actionProps.ActionComponent` in place of the
        // default slot, so unlike the base Dialog it may receive no slots.
        // Override the required `dialogProps.slots` to make it optional.
        slots: t.any().optional(),
        withBodyPadding: t.boolean().optional(false),
    };
    actionProps = useProps({
        ActionComponent: t.any().optional(),
        actionProps: t.any().optional(),
        action: t.any().optional(),
    });

    debugMode = usePlugin(DebugModePlugin);
    actionService = useService("action");

    setup() {
        super.setup();
        useOwnDebugContext();

        const { action } = this.actionProps;
        this.actionComponentProps = { ...this.actionProps.actionProps };
        this.currentResId = this.actionComponentProps?.resId || false;

        const shouldExpand = this.actionComponentProps?.type === "form" && action && action.can_expand;
        if (shouldExpand) {
            this.onExpandCallback = this.onExpand.bind(this);
            this.actionComponentProps.__beforeLeave__ = new CallbackRecorder();
            const originalOnSave = this.actionComponentProps.onSave;
            this.actionComponentProps.onSave = (record, params) => {
                this.currentResId = record.resId;
                originalOnSave?.(record, params);
            };
        }
    }

    async onExpand(_ev, newWindow) {
        const beforeLeaveCallbacks = this.actionComponentProps.__beforeLeave__.callbacks;
        const res = await Promise.all(beforeLeaveCallbacks.map((callback) => callback()));
        if (!res.includes(false)) {
            this.actionService.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: this.actionComponentProps.resModel,
                    res_id: this.currentResId,
                    views: [[false, "form"]],
                    target: "current",
                    context: {
                        ...this.actionComponentProps.context,
                        // unset form_view_ref. We want the default form
                        // to show, we explicitly prevent form_view_ref
                        // to be used.
                        form_view_ref: undefined,
                    },
                },
                { newWindow }
            );
        }
    }
}
