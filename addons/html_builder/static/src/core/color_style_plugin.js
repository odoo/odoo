import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { applyNeededCss } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";

class ColorStylePlugin extends Plugin {
    static id = "colorStyle";
    static dependencies = ["color"];
    resources = {
        apply_style: withSequence(5, (element, cssProp, color) => {
            applyNeededCss(element, cssProp, color);
            return true;
        }),
        apply_custom_css_style: withSequence(20, this.applyColorStyle.bind(this)),
    };
    applyColorStyle({ editingElement, params: { mainParam: styleName = "" }, value }) {
        if (styleName === "background-color") {
            const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
            if (match) {
                value = `bg-${match[1]}`;
            }
            this.dependencies.color.colorElement(editingElement, value, "backgroundColor");
            return true;
        } else if (styleName === "color") {
            const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
            if (match) {
                value = `text-${match[1]}`;
            }
            this.dependencies.color.colorElement(editingElement, value, "color");
            return true;
        }
        return false;
    }
}

registry.category("builder-plugins").add(ColorStylePlugin.id, ColorStylePlugin);
