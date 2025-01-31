import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, onMounted, useRef } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useDomState,
    useBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

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
        const { callOperation } = getAllActionsAndOperations(this);
        this.currentColors = useDomState((editingElement) => ({
            [this.props.styleAction]: editingElement
                ? getComputedStyle(editingElement)[this.props.styleAction]
                : undefined,
        }));
        this.colorButton = useRef("colorButton");
        onMounted(this.updateColorButton.bind(this));
        const applyOperation = this.env.editor.shared.history.makePreviewableOperation(
            (applySpecs) => {
                for (const applySpec of applySpecs) {
                    if (applySpec.actionId === "styleAction") {
                        const styleAction = this.props.styleAction;
                        const applyColor =
                            styleAction === "color" || styleAction === "backgroundColor"
                                ? (element) => {
                                      this.env.editor.shared.color.colorElement(
                                          element,
                                          applySpec.actionValue,
                                          styleAction
                                      );
                                  }
                                : (element) => {
                                      // TODO should support prefix (border- etc )
                                      element.style.setProperty(
                                          styleAction,
                                          applySpec.actionValue,
                                          "important"
                                      );
                                  };
                        applyColor(applySpec.editingElement);
                        this.updateColorButton();
                    } else {
                        applySpec.apply({
                            editingElement: applySpec.editingElement,
                            param: applySpec.actionParam,
                            value: applySpec.actionValue,
                            loadResult: applySpec.loadResult,
                            dependencyManager: this.env.dependencyManager,
                        });
                    }
                }
            }
        );
        this.onCommit = ({ color }) => {
            callOperation(applyOperation.commit, { userValueInput: color });
        };
        this.onPreview = ({ color }) => {
            callOperation(applyOperation.preview, {
                userValueInput: color,
                operationParams: {
                    cancellable: true,
                    cancelPrevious: () => applyOperation.revert(),
                },
            });
        };
        this.onRevert = () => {
            // The `next` will cancel the previous operation, which will revert
            // the operation in case of a preview.
            this.env.editor.shared.operation.next();
        };
    }

    get colorType() {
        // TODO need to ref colorSelector to make it more generic
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
