import { useEffect, useState } from "@odoo/owl";

export function useDropdownAutoVisibility(overlayState, popoverRef) {
    if (!overlayState) {
        return;
    }
    const state = useState(overlayState);
    useEffect(
        () => {
            if (popoverRef.el) {
                if (!state.isOverlayVisible) {
                    popoverRef.el.style.visibility = "hidden";
                } else {
                    popoverRef.el.style.visibility = "visible";
                }
            }
        },
        () => [state.isOverlayVisible]
    );
}
