import { Dialog } from "@web/core/dialog/dialog";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { useOwnDebugContext } from "@web/core/debug/debug_context";

import { useEffect } from "@odoo/owl";

export class ActionDialog extends Dialog {
    static components = { ...Dialog.components, DebugMenu };
    static template = "web.ActionDialog";
    static props = {
        ...Dialog.props,
        close: Function,
        slots: { optional: true },
        ActionComponent: { optional: true },
        actionProps: { optional: true },
        actionType: { optional: true },
        title: { optional: true },
    };
    static defaultProps = {
        ...Dialog.defaultProps,
        withBodyPadding: false,
    };

    setup() {
        super.setup();
        useOwnDebugContext();
        useEffect(
            () => {
                if (this.modalRef.el.querySelector(".modal-footer")?.childElementCount > 1) {
                    const defaultButton = this.modalRef.el.querySelector(
                        ".modal-footer button.o-default-button"
                    );
                    defaultButton.classList.add("d-none");
                }
            },
            () => []
        );
    }
}
