import { registry } from "@web/core/registry";
import { SharedPopup } from "./shared_popup";

export const SharedPopupEdit = (I) => class extends I {
    setup() {
        this.popupShown = true;
    }
};

registry
    .category("public.interactions.edit")
    .add("website.shared_popup", { Interaction: SharedPopup, mixin: SharedPopupEdit });
