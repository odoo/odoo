import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class CarouselSlidesOption extends BaseOptionComponent {
    static template = "website.CarouselSlidesOption";
    static selector = ".carousel .carousel-item";
    static exclude = ".s_image_gallery .carousel-item";
}

export class CarouselSlidesOptionPlugin extends Plugin {
    static id = "carouselSlidesOption";
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC_END, CarouselSlidesOption)],
        builder_actions: {
            MakeSlideClickableAction,
            SetSlideAnchorUrlAction,
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
        legit_empty_link_predicates: (linkEl) => linkEl.matches(".carousel-item a.slide-link"),
    };

    /**
     * Remove `clickable-slide` class from slides when there is no link element.
     * TODO: Find a better approach. The class is currently used so the "active"
     * state of the `BuilderCheckbox` can be taken into account.
     * It would probably be better to handle this via an option state, or adapt
     * the`BuilderCheckbox to expose its 'checkbox active state' when no action
     * is linked to it...
     *
     * @param {HTMLElement} root
     */
    cleanForSave({ root }) {
        const noLinkSlideEls = root.querySelectorAll(
            ".carousel-item.clickable-slide:not(:has(.slide-link))"
        );
        for (const slideEl of noLinkSlideEls) {
            slideEl.classList.remove("clickable-slide");
        }
    }
}

class MakeSlideClickableAction extends BuilderAction {
    static id = "makeSlideClickable";
    setup() {
        this.preview = false;
    }
    clean({ editingElement }) {
        // Remove unnecessary link from the slide when toggled off.
        const linkEl = editingElement.querySelector("a.slide-link");
        linkEl?.remove();
    }
}

/**
 * Custom action to add, update, or remove a slide-link for clickable carousel
 * slides.
 */
class SetSlideAnchorUrlAction extends BuilderAction {
    static id = "setSlideAnchorUrl";
    setup() {
        this.preview = false;
    }
    apply({ editingElement, value }) {
        const url = value;
        const linkEl = editingElement.querySelector("a.slide-link");

        if (!url) {
            linkEl.remove();
            return;
        }
        if (linkEl) {
            linkEl.setAttribute("href", url);
            return;
        }
        const anchorEl = document.createElement("a");
        anchorEl.className = "slide-link position-absolute top-0 start-0 w-100 h-100 d-none";
        anchorEl.setAttribute("href", url);
        anchorEl.style.zIndex = 100;
        editingElement.prepend(anchorEl);
    }
    getValue({ editingElement }) {
        const linkEl = editingElement.querySelector("a.slide-link");
        return linkEl?.getAttribute("href") || "";
    }
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
