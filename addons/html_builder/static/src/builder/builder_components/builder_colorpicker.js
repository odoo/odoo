import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, onMounted, useRef } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useDomState,
    useBuilderComponent,
    BuilderComponent,
} from "./utils";

export class BuilderColorpicker extends Component {
    static template = "html_builder.BuilderColorpicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        unit: { type: String, optional: true },
    };
    static components = {
        ColorSelector,
        BuilderComponent,
    };

    setup() {
        useBuilderComponent();
        this.currentColors = useDomState((editingElement) => ({
            backgroundColor: editingElement
                ? getComputedStyle(editingElement).backgroundColor
                : undefined,
        }));
        this.colorButton = useRef("colorButton");
        onMounted(this.updateColorButton.bind(this));
        this.applyColor = this.env.editor.shared.history.makePreviewableOperation(
            ({ color, mode }) => {
                for (const element of this.env.getEditingElements()) {
                    this.env.editor.shared.color.colorElement(element, color, "backgroundColor");
                }

                this.updateColorButton();
            }
        );
    }
    updateColorButton() {
        const editingElement = this.env.getEditingElement();
        if (!this.colorButton.el || !editingElement) {
            return;
        }
        const color =
            this.env.editor.shared.color.getElementColors(editingElement)["backgroundColor"];
        this.env.editor.shared.color.colorElement(this.colorButton.el, color, "backgroundColor");
    }
}
