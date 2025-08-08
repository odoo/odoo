import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { getSelectorParams } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { WebsiteBackgroundOption } from "./background_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { withSequence } from "@html_editor/utils/resource";
class WebsiteParallaxPlugin extends Plugin {
    static id = "websiteParallaxPlugin";
    static dependencies = ["builderActions", "backgroundImageOption"];
    static shared = ["applyParallaxType"];
    resources = {
        builder_actions: {
            SetParallaxTypeAction,
        },
        on_bg_image_hide_handlers: this.onBgImageHide.bind(this),
        force_not_editable_selector: ".s_parallax_bg, section.s_parallax > .oe_structure",
        get_target_element_providers: withSequence(1, this.getTargetElement),
    };
    setup() {
        this.backgroundOptionSelectorParams = getSelectorParams(
            this.getResource("builder_options"),
            WebsiteBackgroundOption
        );
    }
    applyParallaxType({ editingElement, value }) {
        const isParallax = value !== "none";
        editingElement.classList.toggle("parallax", isParallax);
        editingElement.classList.toggle("s_parallax_is_fixed", value === "fixed");
        editingElement.classList.toggle(
            "s_parallax_no_overflow_hidden",
            value === "none" || value === "fixed"
        );
        const typeValues = {
            none: 0,
            fixed: 1,
            top: 1.5,
            bottom: -1.5,
            zoom_in: 1.2,
            zoom_out: 0.2,
        };
        editingElement.dataset.scrollBackgroundRatio = typeValues[value];
        // Set a parallax type only if there is a zoom option selected.
        // This is to avoid useless element in the DOM since in the animation
        // we need the type only for zoom options.
        if (value === "zoom_in" || value === "zoom_out") {
            editingElement.dataset.parallaxType = value;
        } else {
            delete editingElement.dataset.parallaxType;
        }
        let parallaxEl = editingElement.querySelector(":scope > .s_parallax_bg");
        if (isParallax) {
            if (!parallaxEl) {
                parallaxEl = document.createElement("span");
                parallaxEl.classList.add("s_parallax_bg");
                editingElement.prepend(parallaxEl);
                this.dependencies.backgroundImageOption.changeEditingEl(editingElement, parallaxEl);
            }
        } else if (parallaxEl) {
            this.dependencies.backgroundImageOption.changeEditingEl(parallaxEl, editingElement);
            parallaxEl.remove();
        }
    }
    onBgImageHide(rootEl) {
        for (const backgroundOptionSelector of this.backgroundOptionSelectorParams) {
            applyFunDependOnSelectorAndExclude(
                this.removeParallax.bind(this),
                rootEl,
                backgroundOptionSelector
            );
        }
    }
    removeParallax(editingEl) {
        const parallaxEl = editingEl.querySelector(":scope > .s_parallax_bg");
        const bgImage = parallaxEl?.style.backgroundImage;
        if (
            !parallaxEl ||
            !bgImage ||
            bgImage === "none" ||
            editingEl.classList.contains("o_background_video")
        ) {
            // The parallax option was enabled but the background image was
            // removed or a background video has been added: disable the
            // parallax option.
            this.applyParallaxType({
                editingElement: editingEl,
                value: "none",
            });
        }
    }
    getTargetElement(editingEl) {
        return editingEl.classList.contains("s_parallax_bg") ? editingEl.parentElement : editingEl;
    }
}
export class SetParallaxTypeAction extends BuilderAction {
    static id = "setParallaxType";
    static dependencies = ["websiteParallaxPlugin"];
    apply(context) {
        this.dependencies.websiteParallaxPlugin.applyParallaxType(context);
    }
    isApplied({ editingElement, value }) {
        const attributeValue = parseFloat(
            editingElement.dataset.scrollBackgroundRatio?.trim() || 0
        );
        if (attributeValue === 0) {
            return value === "none";
        }
        if (attributeValue === 1) {
            return value === "fixed";
        }
        const parallaxType = editingElement.dataset.parallaxType;
        if (parallaxType) {
            return value === parallaxType;
        }
        return attributeValue > 0 ? value === "top" : value === "bottom";
    }
}

registry.category("website-plugins").add(WebsiteParallaxPlugin.id, WebsiteParallaxPlugin);
