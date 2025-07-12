import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { CSS_SHORTHANDS } from "@html_builder/utils/utils_css";

class BorderRadiusStylePlugin extends Plugin {
    static id = "borderRadiusStyle";
    resources = {
        apply_custom_css_style: withSequence(20, this.applyRadiusStyle.bind(this)),
    };

    // border-radius calculation using --box-border-radius variables is
    // done at class level using .rounded, so eventual border-radius styles
    // must be removed beacuse they would otherwise take precedence
    applyRadiusStyle({ editingElement, params, value }) {
        if (
            params.mainParam === "--box-border-radius" ||
            CSS_SHORTHANDS["--box-border-radius"].includes(params.mainParam)
        ) {
            editingElement.style.setProperty("border-radius", "");
        }
        return false;
    }
}

registry.category("website-plugins").add(BorderRadiusStylePlugin.id, BorderRadiusStylePlugin);
