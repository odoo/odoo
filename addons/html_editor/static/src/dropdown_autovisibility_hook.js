import { useEffect } from "@odoo/owl";

export function useDropdownAutoVisibility(overlayState, menuRef) {
    if (!overlayState) {
        return;
    }
    useEffect(
        () => {
            if (menuRef.el) {
                if (!overlayState.isOverlayVisible) {
                    menuRef.el.style.visibility = "hidden";
                } else {
                    menuRef.el.style.visibility = "visible";
                }
            }
        },
        () => [overlayState.isOverlayVisible]
    );
}
