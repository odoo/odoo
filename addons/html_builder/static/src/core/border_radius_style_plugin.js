import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { CSS_SHORTHANDS } from "@html_builder/utils/utils_css";

class BorderRadiusStylePlugin extends Plugin {
    static id = "borderRadiusStyle";
    resources = {
        apply_custom_css_style: withSequence(20, this.applyRadiusStyle.bind(this)),
    };

    // border-width/radius calculation using --box-border-width/radius
    // variables is done at class level using .border and.rounded, so
    // eventual border-width/radius styles must be removed beacuse
    // they would otherwise take precedence
    applyRadiusStyle({ editingElement, params }) {
        if (
            editingElement.style["border-width"] &&
            (params.mainParam === "--box-border-width" ||
                CSS_SHORTHANDS["--box-border-width"].includes(params.mainParam))
        ) {
            editingElement.style.setProperty("border-width", "");
            this.removeChildRadiusStyle(editingElement);
        } else if (
            editingElement.style["border-radius"] &&
            (params.mainParam === "--box-border-radius" ||
                CSS_SHORTHANDS["--box-border-radius"].includes(params.mainParam))
        ) {
            editingElement.style.setProperty("border-radius", "");
            this.removeChildRadiusStyle(editingElement);
        }
        return false;
    }

    // Also remove style from children with %o-we-background-layer
    // classes since it's not needed thanks to the .border and
    // .rounded classes
    removeChildRadiusStyle(editingElement) {
        editingElement.childNodes.forEach((childNode) => {
            if (
                childNode.classList &&
                ["o_we_bg_filter", "o_we_shape", "o_bg_video_container", "s_parallax_bg"].some(
                    (backgroundLayerExtensions) =>
                        childNode.classList.contains(backgroundLayerExtensions)
                )
            ) {
                if (editingElement.style["border-radius"]) {
                    childNode.style.setProperty("border-radius", "");
                }
            }
        });
    }
}

registry.category("website-plugins").add(BorderRadiusStylePlugin.id, BorderRadiusStylePlugin);
