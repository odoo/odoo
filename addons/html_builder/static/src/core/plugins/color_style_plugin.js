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
                    if (value.startsWith("color-prefix-")) {
                        value = value.replace("color-prefix-", "bg-");
                    }
                    this.dependencies.color.colorElement(editingElement, value, "backgroundColor");
                },
            },
            color: {
                getValue: (editingElement) =>
                    this.dependencies.color.getElementColors(editingElement)["color"],
                apply: (editingElement, value) => {
                    if (value.startsWith("color-prefix-")) {
                        value = value.replace("color-prefix-", "text-");
                    }
                    this.dependencies.color.colorElement(editingElement, value, "color");
                },
            },
        };
    }
}
registry.category("website-plugins").add(ColorStylePlugin.id, ColorStylePlugin);
