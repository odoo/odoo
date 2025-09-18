// @ts-check

/** @module @web/views/calendar/hooks/calendar_popover_hook - Hook managing calendar event popovers with desktop/mobile responsive behavior */

import { useComponent, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/ui/popover/popover_hook";

/**
 * OWL hook that manages calendar event popovers with responsive behavior.
 *
 * On desktop, opens a positioned popover anchored to the event element.
 * On mobile, opens a full dialog instead. Prevents FullCalendar's own
 * popover from closing while the custom popover is open.
 *
 * @param {typeof Component} component - OWL component class to render inside the popover
 * @returns {{ close: Function, open: Function }} popover control API
 */
export function useCalendarPopover(component) {
    const owner = useComponent();
    let popoverClass = "";
    /** @type {any} */
    const popoverOptions = {
        extendedFlipping: true,
        position: "right",
        onClose: cleanup,
    };
    Object.defineProperty(popoverOptions, "popoverClass", {
        get: () => popoverClass,
    });
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
        { capture: true },
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
                removeDialog = dialog.add(component, props, {
                    onClose: cleanup,
                });
            } else {
                popoverClass = popoverClassToUse;
                popover.open(target, props);
            }
        },
    };
}
