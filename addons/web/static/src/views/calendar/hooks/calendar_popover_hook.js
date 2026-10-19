import { usePopover } from "@web/core/popover/popover_hook";
import { useListener } from "@odoo/owl";

export function useCalendarPopover(component) {
    let popoverClass = "";
    const popoverOptions = { position: "right", onClose: cleanup };
    Object.defineProperty(popoverOptions, "popoverClass", { get: () => popoverClass });
    const popover = usePopover(component, popoverOptions);
    let removeDialog = null;
    let fcPopover;
    useListener(
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
            popoverClass = popoverClassToUse;
            popover.open(target, props);
        },
        get isOpen() {
            return popover.isOpen;
        },
    };
}
