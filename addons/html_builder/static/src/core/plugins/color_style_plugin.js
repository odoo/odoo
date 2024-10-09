import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ColorStylePlugin extends Plugin {
    static id = "ColorStyle";
    static dependencies = ["color"];
    resources = {
        builder_style_actions: this.getStyleActions(),
    };

    getStyleActions() {
        return {
            "background-color": {
                getValue: (editingElement) =>
                    this.dependencies.color.getElementColors(editingElement)["backgroundColor"],
                apply: (editingElement, value) => {
                    const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
                    if (match) {
                        value = `bg-${match[1]}`;
                    }
                    this.dependencies.color.colorElement(editingElement, value, "backgroundColor");
                },
            },
            color: {
                getValue: (editingElement) =>
                    this.dependencies.color.getElementColors(editingElement)["color"],
                apply: (editingElement, value) => {
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
