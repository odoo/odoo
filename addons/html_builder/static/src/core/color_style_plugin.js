import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { applyNeededCss } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";

class ColorStylePlugin extends Plugin {
    static id = "colorStyle";
    static dependencies = ["color"];
    resources = {
        builder_style_actions: {
            BackgroundColorAction,
            ColorAction,
        },
        apply_style: withSequence(5, (element, cssProp, color) => {
            applyNeededCss(element, cssProp, color);
            return true;
        }),
    };
}

class BackgroundColorAction extends BuilderAction {
    static id = "background-color";
    static dependencies = ["color"];
    getValue(el) {
        return this.dependencies.color.getElementColors(el)["backgroundColor"];
    }
    apply(el, value) {
        const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
        if (match) {
            value = `bg-${match[1]}`;
        }
        this.dependencies.color.colorElement(el, value, "backgroundColor");
    }
}

class ColorAction extends BuilderAction {
    static id = "color";
    static dependencies = ["color"];
    getValue(el) {
        console.log(el);
        return this.dependencies.color.getElementColors(el)["color"];
    }
    apply(el, value) {
        const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
        if (match) {
            value = `text-${match[1]}`;
        }
        this.dependencies.color.colorElement(el, value, "color");
    }
}

registry.category("website-plugins").add(ColorStylePlugin.id, ColorStylePlugin);
