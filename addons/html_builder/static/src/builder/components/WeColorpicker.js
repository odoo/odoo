import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, onMounted, useRef } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useDomState,
    useWeComponent,
    WeComponent,
} from "../builder_helpers";

export class WeColorpicker extends Component {
    static template = "html_builder.WeColorpicker";
    static props = {
        ...basicContainerWeWidgetProps,
        unit: { type: String, optional: true },
    };
    static components = {
        ColorSelector,
        WeComponent,
    };

    setup() {
        useWeComponent();
        this.currentColors = useDomState((editingElement) => ({
            backgroundColor: editingElement
                ? getComputedStyle(editingElement).backgroundColor
                : undefined,
        }));
        this.colorButton = useRef("colorButton");
        onMounted(this.updateColorButton.bind(this));
        this.applyColor = this.env.editor.shared.history.makePreviewableOperation(
            ({ color, mode }) => {
                this.env.editor.shared.color.colorElement(
                    this.env.getEditingElement(),
                    color,
                    "backgroundColor"
                );
                this.updateColorButton();
            }
        );
    }
    updateColorButton() {
        if (!this.colorButton.el || !this.env.getEditingElement()) {
            return;
        }
        const color = this.env.editor.shared.color.getElementColors(this.env.getEditingElement())[
            "backgroundColor"
        ];
        this.env.editor.shared.color.colorElement(this.colorButton.el, color, "backgroundColor");
    }
}
