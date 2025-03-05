import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { applyNeededCss } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";

class ColorStylePlugin extends Plugin {
    static id = "colorStyle";
    static dependencies = ["color"];
    resources = {
        builder_style_actions: this.getStyleActions(),
        apply_color_style: withSequence(5, (element, mode, color) => {
            applyNeededCss(element, mode === "backgroundColor" ? "background-color" : mode, color);
            return true;
        }),
    };

    getStyleActions() {
        return {
            "background-color": {
                getValue: ({ editingElement }) =>
                    this.dependencies.color.getElementColors(editingElement)["backgroundColor"],
                apply: ({ editingElement, value }) => {
                    const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
                    if (match) {
                        value = `bg-${match[1]}`;
                    }
                    this.dependencies.color.colorElement(editingElement, value, "backgroundColor");
                },
            },
            color: {
                getValue: ({ editingElement }) =>
                    this.dependencies.color.getElementColors(editingElement)["color"],
                apply: ({ editingElement, value }) => {
                    const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
                    if (match) {
                        value = `text-${match[1]}`;
                    }
                    this.dependencies.color.colorElement(editingElement, value, "color");
                },
            },
        };
    }
}
registry.category("website-plugins").add(ColorStylePlugin.id, ColorStylePlugin);
