import { SharedPopup } from "./shared_popup";
import { registry } from "@web/core/registry";

export const SharedPopupEdit = (I) =>
    class extends I {
        setup() {
            // Sync the status of the popup in the editor with its visibility
            // status `data-invisible`
            this.popupShown = this.el.dataset.invisible !== "1";
        }
    };

registry.category("public.interactions.edit").add("website.shared_popup", {
    Interaction: SharedPopup,
    mixin: SharedPopupEdit,
});
