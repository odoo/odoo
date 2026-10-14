import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SharedPopup extends Interaction {
    static selector = ".s_popup";
    dynamicContent = {
        // There used to be some logic that added a "d-none" to force hide the
        // popup element, but this is now handled in css by forcing the height
        // to 0 on #website_cookies_bar
        // And we need to still show the ones that have been saved with it.
        _root: {
            "t-on-hidden.bs.modal": this.onModalHidden,
            "t-att-class": () => ({ "d-none": false }),
        },
    };

    onModalHidden() {
        if (this.el.querySelector(".s_popup_no_backdrop")) {
            // We trigger a scroll event here to call the
            // '_hideBottomFixedElements' method and re-display any bottom fixed
            // elements that may have been hidden (e.g. the live chat button
            // hidden when the cookies bar is open).
            window.dispatchEvent(new Event("scroll"));
        }
    }
}

registry.category("public.interactions").add("website.shared_popup", SharedPopup);
registry
    .category("public.interactions.edit")
    .add("website.shared_popup", { Interaction: SharedPopup });
