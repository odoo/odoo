import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, onMounted, useRef } from "@odoo/owl";
import { basicContainerWeWidgetProps, useWeComponent } from "../builder_helpers";

export class WeColorpicker extends Component {
    static template = "html_builder.WeColorpicker";
    static props = {
        ...basicContainerWeWidgetProps,
        unit: { type: String, optional: true },
    };
    static components = {
        ColorSelector,
    };

    setup() {
        useWeComponent();
        const color = getComputedStyle(this.env.editingElement).backgroundColor;
        this.currentColors = {
            backgroundColor: color,
        };
        this.colorButton = useRef("colorButton");
        onMounted(this.updateColorButton.bind(this));
        this.applyColor = this.env.editor.shared.history.makePreviewableOperation(
            ({ color, mode }) => {
                this.env.editor.shared.color.colorElement(
                    this.env.editingElement,
                    color,
                    "backgroundColor"
                );
                this.updateColorButton();
            }
        );
    }
    updateColorButton() {
        if (!this.colorButton.el) {
            return;
        }
        const color = this.env.editor.shared.color.getElementColors(this.env.editingElement)[
            "backgroundColor"
        ];
        this.env.editor.shared.color.colorElement(this.colorButton.el, color, "backgroundColor");
    }
}
