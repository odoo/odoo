import { applyFunDependOnSelectorAndExclude } from "@website/builder/plugins/utils";
import { getSelectorParams } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { WebsiteBackgroundOption } from "./background_option";
import { BuilderAction } from "@html_builder/core/builder_action";
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
        // Kept for compatibility. The "s_parallax_no_overflow_hidden" class may
        // still appear when "s_parallax_bg" hasn’t yet been wrapped in
        // "s_parallax_bg_wrap".
        editingElement.classList.remove("s_parallax_no_overflow_hidden");
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

        let parallaxBgEl = editingElement.querySelector(".s_parallax_bg");
        const parallaxBgWrapEl = editingElement.querySelector(".s_parallax_bg_wrap");
        if (isParallax) {
            if (!parallaxBgEl) {
                parallaxBgEl = document.createElement("span");
                parallaxBgEl.classList.add("s_parallax_bg");
                this.dependencies.backgroundImageOption.changeEditingEl(editingElement, parallaxBgEl);
            }
            // For compatibility, check if not "parallaxBgWrapEl" separately.
            // "parallaxBgEl" may exist without "parallaxBgWrapEl".
            if (!parallaxBgWrapEl) {
                const newWrapEl = document.createElement("span");
                newWrapEl.classList.add("s_parallax_bg_wrap");
                newWrapEl.appendChild(parallaxBgEl);
                editingElement.prepend(newWrapEl);
            }
        } else if (parallaxBgEl) {
            this.dependencies.backgroundImageOption.changeEditingEl(parallaxBgEl, editingElement);
            if (parallaxBgWrapEl) {
                parallaxBgWrapEl.remove();
            } else {
                parallaxBgEl.remove(); // Kept for compatibility.
            }
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
        const parallaxEl = editingEl.querySelector(".s_parallax_bg");
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
