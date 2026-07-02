import { props, t } from "@odoo/owl";
import { Dialog, dialogProps } from "@web/core/dialog/dialog";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { useOwnDebugContext } from "@web/core/debug/debug_context";

export class ActionDialog extends Dialog {
    static components = { ...Dialog.components, DebugMenu };
    static template = "web.ActionDialog";
    static props = {
        ...dialogProps,
        // ActionDialog renders `actionProps.ActionComponent` in place of the
        // default slot, so unlike the base Dialog it may receive no slots.
        // Override the required `dialogProps.slots` to make it optional.
        slots: t.any().optional(),
        withBodyPadding: t.boolean().optional(false),
    };
    actionProps = props({
        ActionComponent: t.any().optional(),
        actionProps: t.any().optional(),
        actionType: t.any().optional(),
    });

    setup() {
        super.setup();
        useOwnDebugContext();
    }
}
