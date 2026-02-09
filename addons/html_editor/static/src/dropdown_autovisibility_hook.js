import { useLayoutEffect, useState } from "@web/owl2/utils";

export function useDropdownAutoVisibility(overlayState, popoverRef) {
    if (!overlayState) {
        return;
    }
    const state = useState(overlayState);
    useLayoutEffect(
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
