import { registry } from "@web/core/registry";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { Interaction } from "@web/public/interaction";

export class SharedPopup extends Interaction {
    static selector = ".s_popup";
    dynamicContent = {
        // A popup element is composed of a `.s_popup` parent containing the
        // actual `.modal` BS modal. Our internal logic and events are hiding
        // and showing this inner `.modal` modal element without considering its
        // `.s_popup` parent. It means that when the `.modal` is hidden, its
        // `.s_popup` parent is not touched and kept visible.
        // It might look like it's not an issue as it would just be an empty
        // element (its only child is hidden) but it leads to some issues as for
        // instance on chrome this div will have a forced `height` due to its
        // `contenteditable=true` attribute in edit mode. It will result in a
        // ugly white bar.
        // tl;dr: this is keeping those 2 elements visibility synchronized.
        "_root": {
            "t-on-show.bs.modal": () => this.popupShown = true,
            "t-on-hidden.bs.modal": this.onModalHidden,
            "t-att-class": () => ({ "d-none": !this.popupShown }),
        },
    }

    setup() {
        this.popupShown = false;
    }

    onModalHidden() {
        if (this.el.querySelector(".s_popup_no_backdrop")) {
            // We trigger a scroll event here to call the
            // '_hideBottomFixedElements' method and re-display any bottom fixed
            // elements that may have been hidden (e.g. the live chat button
            // hidden when the cookies bar is open).
            getScrollingElement().dispatchEvent(new Event("scroll"));
        }
        this.popupShown = false;
    }
}

registry
    .category("public.interactions")
    .add("website.shared_popup", SharedPopup);

registry
    .category("public.interactions.edit")
    .add("website.shared_popup", { Interaction: SharedPopup });
