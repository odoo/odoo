import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import { useComponent, useExternalListener } from "@odoo/owl";

export function useCalendarPopover(component) {
    const owner = useComponent();
    let popoverClass = "";
    const popoverOptions = { position: "right", onClose: cleanup };
    Object.defineProperty(popoverOptions, "popoverClass", { get: () => popoverClass });
    const popover = usePopover(component, popoverOptions);
    const dialog = useService("dialog");
    let removeDialog = null;
    let fcPopover;
    useExternalListener(
        window,
        "mousedown",
        (ev) => {
            if (fcPopover) {
                // do not let fullcalendar popover close when our own popover is open
                ev.stopPropagation();
            }
        },
        { capture: true }
    );
    function cleanup() {
        fcPopover = null;
        removeDialog = null;
    }
    function close() {
        removeDialog?.();
        popover.close();
        cleanup();
    }
    return {
        close,
        open(target, props, popoverClassToUse) {
            fcPopover = target.closest(".fc-popover");
            if (owner.env.isSmall) {
                close();
                removeDialog = dialog.add(component, props, { onClose: cleanup });
            } else {
                popoverClass = popoverClassToUse;
                popover.open(target, props);
            }
        },
    };
}
