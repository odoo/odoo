import { NoBackdropPopup } from "./no_backdrop_popup";
import { registry } from "@web/core/registry";

export const NoBackdropPopupEdit = (I) => class extends I {
    start() {
        super.start();
        if (this.el.classList.contains("show")) {
            // Use case: When the "Backdrop" option is disabled in edit mode.
            // The page scrollbar must be adjusted and events must be added.
            this.addModalNoBackdropEvents();
        }
    }

    addModalNoBackdropEvents() {
        // We shouldn't normally go through this 2x without removing the
        // observers in between, but it happens when opening the editor (start)
        // and then showing the popup (dynamicContent listener).
        if (this.resizeObserver) {
            this.removeResizeListener();
            this.resizeObserver.disconnect();
        }
        super.addModalNoBackdropEvents();
    }
};

registry
    .category("public.interactions.edit")
    .add("website.no_backdrop_popup", {
        Interaction: NoBackdropPopup,
        mixin: NoBackdropPopupEdit,
    });
