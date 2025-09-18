// @ts-check

/** @module @web/webclient/actions/action_dialog - Dialog subclass for rendering action components (target="new") with debug menu integration */

import { useOwnDebugContext } from "@web/services/debug/debug_context";
import { DebugMenu } from "@web/services/debug/debug_menu";
import { Dialog } from "@web/ui/dialog/dialog";

/**
 * Dialog subclass for rendering action components (target="new").
 * Extends Dialog with an ActionComponent slot and debug menu integration.
 */
export class ActionDialog extends Dialog {
    static components = {
        .../** @type {any} */ (Dialog).components,
        DebugMenu,
    };
    static template = "web.ActionDialog";
    static props = {
        .../** @type {any} */ (Dialog).props,
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
    }
}
