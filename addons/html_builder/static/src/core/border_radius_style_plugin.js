import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { CSS_SHORTHANDS } from "@html_builder/utils/utils_css";

/**
 * Compatibility plugin to handle border-width and border-radius inline style
 * removal (including from inner layers), as the calculation regarding radius of
 * inner layers is now automatically done in CSS via the improved bootstrap
 * rounded-X classes and CSS variables.
 */

const NEW_STYLES = ["--box-border-width", "--box-border-radius"];
const OLD_STYLES = ["border-width", "border-radius"];

export class CompatibilityInlineBorderRemovalPlugin extends Plugin {
    static id = "compatibilityInlineBorderRemoval";
    resources = {
        apply_custom_css_style: withSequence(20, this.removeInlineBorderIfNecessary.bind(this)),
    };

    // The border-width/radius calculation using --box-border-width/radius
    // variables is done at class level using "border" and "rounded" classes, so
    // eventual border-width/radius styles must be removed because they would
    // otherwise take precedence.
    removeInlineBorderIfNecessary({ editingElement, params }) {
        const newStyleBeingEdited = NEW_STYLES.find(style => {
            return params.mainParam === style
                || CSS_SHORTHANDS[style].includes(params.mainParam);
        });
        if (newStyleBeingEdited && OLD_STYLES.some(style => editingElement.style[style])) {
            // Remove all old inline styles related to border-width/radius as
            // the new CSS rules + variables rely on both being right, i.e. not
            // messed up by any inline style...
            for (const oldStyle of OLD_STYLES) {
                // TODO even though the part about inner layers below is pure
                // compatibility, this here should actually be done as the
                // main feature: editing a CSS variable which controls an unique
                // property should really enforce removing that property if
                // already forced as inline style. See CSS_VARIABLE_EDIT_TODO.
                editingElement.style.setProperty(oldStyle, "");
            }
            // ... that is why we just always remove inner radius style from
            // children with %o-we-background-layer classes too (note: the code
            // that handled adding inline style on child nodes only handled
            // those specific ones here after).
            const compatLayerSelectors = [".o_we_bg_filter", ".o_bg_video_container", ".s_parallax_bg"];
            const selector = `:scope > ${compatLayerSelectors.join(", :scope > ")}`;
            for (const childNode of editingElement.querySelectorAll(selector)) {
                childNode.style.setProperty("border-radius", "");
            }
        }
        return false;
    }
}

registry.category("website-plugins")
    .add(CompatibilityInlineBorderRemovalPlugin.id, CompatibilityInlineBorderRemovalPlugin);
