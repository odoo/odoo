import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteSlidesStickyObject extends Interaction {
    static selector = ".o_wslides_course_sidebar";

    dynamicContent = {
        _root: {
            "t-att-style": () => ({
                "top": `${this.position || 16}px`,
            }),
        }
    };

    setup() {
        this.position = 16;
    }

    start() {
        this._adaptToHeaderChange();
        this.registerCleanup(this.services.website_menus.registerCallback(this._adaptToHeaderChange.bind(this)));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */

    _adaptToHeaderChange() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default

        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            position += el.offsetHeight;
        }

        if (this.position !== position) {
            this.position = position;
            this.updateContent();
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.sticky_sidebar", WebsiteSlidesStickyObject);

registry
    .category("public.interactions.edit")
    .add("website_slides.sticky_sidebar", { Interaction: WebsiteSlidesStickyObject});
