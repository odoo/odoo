import { useEffect, useState } from "@odoo/owl";

export function useDropdownAutoVisibility(overlayState, menuRef) {
    if (!overlayState) {
        return;
    }
    const state = useState(overlayState);
    useEffect(
        () => {
            if (menuRef.el) {
                if (!state.isOverlayVisible) {
                    menuRef.el.style.visibility = "hidden";
                } else {
                    menuRef.el.style.visibility = "visible";
                }
            }
        },
        () => [state.isOverlayVisible]
    );
}
