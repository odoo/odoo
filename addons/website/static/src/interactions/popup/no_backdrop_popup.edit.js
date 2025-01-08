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
};

registry
    .category("public.interactions.edit")
    .add("website.no_backdrop_popup", {
        Interaction: NoBackdropPopup,
        mixin: NoBackdropPopupEdit,
    });
