import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { applyNeededCss } from "@html_builder/utils/utils_css";

class BorderRadiusStylePlugin extends Plugin {
    static id = "borderRadiusStyle";
    resources = {
        builder_style_actions: this.getStyleActions(),
        step_added_handlers: () => {
            this.document.querySelectorAll(".o_grid_item").forEach((gridEl) => {
                this.calculateAndSetRadius(gridEl);
            });
        },
    };

    getStyleActions() {
        return {
            "border-radius": {
                getValue: (el, styleName) => window.getComputedStyle(el)[styleName],
                apply: (el, styleValue) => {
                    applyNeededCss(el, "border-radius", styleValue);
                    this.calculateAndSetRadius(el);
                },
            },
        };
    }

    calculateAndSetRadius(parentElement) {
        const backgroundEls = parentElement.querySelectorAll(":scope > [class*='_bg']");
        backgroundEls.forEach((backgroundEl) => {
            backgroundEl.style.borderRadius =
                Math.max(
                    0,
                    (parseInt(parentElement.style.borderRadius) || 0) -
                        (parseInt(parentElement.style.borderWidth) || 0)
                ) + "px";
        });
    }
}
registry.category("website-plugins").add(BorderRadiusStylePlugin.id, BorderRadiusStylePlugin);
