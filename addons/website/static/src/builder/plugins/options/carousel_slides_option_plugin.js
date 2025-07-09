import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class CarouselSlidesOptionPlugin extends Plugin {
    static id = "carouselSlidesOption";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.CarouselSlidesOption",
                selector: ".carousel .carousel-item",
                exclude: ".s_image_gallery .carousel-item",
            }),
        ],
        builder_actions: {
            SetSlideLinkAction,
        },
    };
}

class SetSlideLinkAction extends BuilderAction {
    static id = "setSlideLink";
    setup() {
        this.preview = false;
    }
    apply({ editingElement }) {
        const linkEl = editingElement.querySelector("a.slide-link");
        if (linkEl) {
            linkEl.parentElement.remove();
        } else {
            const wrapperEl = document.createElement("div");
            wrapperEl.className =
                "slide-link-wrapper position-absolute top-0 start-0 d-block w-100 h-100 z-n1 o_not_editable";
            wrapperEl.setAttribute("contenteditable", "false");

            const anchorEl = document.createElement("a");
            anchorEl.className = "slide-link slide-link-hover d-block w-100 h-100";

            wrapperEl.appendChild(anchorEl);
            editingElement.prepend(wrapperEl);
        }
    }
    isApplied({ editingElement }) {
        const linkEl = editingElement.querySelector("a.slide-link");
        return !!linkEl;
    }
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
