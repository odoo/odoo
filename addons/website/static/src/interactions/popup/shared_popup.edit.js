import { SharedPopup } from "./shared_popup";
import { registry } from "@web/core/registry";

export const SharedPopupEdit = (I) =>
    class extends I {
        setup() {
            this.popupShown = true;
        }
    };

registry.category("public.interactions.edit").add("website.shared_popup", {
    Interaction: SharedPopup,
    mixin: SharedPopupEdit,
});
