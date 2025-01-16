import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, onMounted, useRef } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useDomState,
    useBuilderComponent,
    BuilderComponent,
} from "./utils";

export class BuilderColorPicker extends Component {
    static template = "html_builder.BuilderColorPicker";
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
            [this.props.styleAction]: editingElement
                ? getComputedStyle(editingElement)[this.props.styleAction]
                : undefined,
        }));
        this.colorButton = useRef("colorButton");
        onMounted(this.updateColorButton.bind(this));
        this.applyColor = this.env.editor.shared.history.makePreviewableOperation(
            ({ color, mode }) => {
                for (const element of this.env.getEditingElements()) {
                    this.env.editor.shared.color.colorElement(
                        element,
                        color,
                        this.props.styleAction
                    );
                }

                this.updateColorButton();
            }
        );
    }

    get colorType() {
        return this.props.styleAction === "color" ? "foreground" : "background";
    }

    updateColorButton() {
        const editingElement = this.env.getEditingElement();
        if (!this.colorButton.el || !editingElement) {
            return;
        }
        const color =
            this.env.editor.shared.color.getElementColors(editingElement)[this.props.styleAction] ||
            editingElement.style[this.props.styleAction] ||
            "";
        this.env.editor.shared.color.colorElement(this.colorButton.el, color, "backgroundColor");
    }
}
