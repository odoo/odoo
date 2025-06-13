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
            MakeSlideClickableAction,
            SetSlideAnchorUrlAction,
        },
    };
}

class MakeSlideClickableAction extends BuilderAction {
    static id = "makeSlideClickable";
    setup() {
        this.preview = false;
    }
    clean({ editingElement }) {
        // Remove unnecessary link wrapper from the slide when toggled off.
        const wrapperEl = editingElement.querySelector("div.slide-link-wrapper");
        wrapperEl?.remove();
    }
}

class SetSlideAnchorUrlAction extends BuilderAction {
    static id = "setSlideAnchorUrl";
    setup() {
        this.preview = false;
    }
    apply({ editingElement, value }) {
        const url = value;
        const linkEl = editingElement.querySelector("a.slide-link");

        // Remove wrapper if no URL
        if (!url) {
            linkEl.parentElement.remove();
            return;
        }
        // If link already exists, just update its href
        if (linkEl) {
            linkEl.setAttribute("href", url);
            return;
        }
        // Otherwise, create and insert the link wrapper
        const wrapperEl = document.createElement("div");
        wrapperEl.className =
            "slide-link-wrapper position-absolute top-0 start-0 w-100 h-100 o_not_editable d-none";
        wrapperEl.style.zIndex = 100;
        wrapperEl.setAttribute("contenteditable", "false");

        const anchorEl = document.createElement("a");
        anchorEl.className = "slide-link d-block w-100 h-100";
        anchorEl.setAttribute("href", url);

        wrapperEl.appendChild(anchorEl);
        editingElement.prepend(wrapperEl);
    }
    getValue({ editingElement }) {
        const linkEl = editingElement.querySelector("a.slide-link");
        return linkEl?.getAttribute("href") || "";
    }
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
