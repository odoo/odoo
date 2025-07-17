import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, useComponent, useRef } from "@odoo/owl";
import { useColorPicker } from "@web/core/color_picker/color_picker";
import { BuilderComponent } from "./builder_component";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDomState,
    useHasPreview,
} from "../utils";
import { isColorGradient } from "@web/core/utils/colors";
import { getAllUsedColors } from "@html_builder/utils/utils_css";

// TODO replace by useInputBuilderComponent after extract unit by AGAU
export function useColorPickerBuilderComponent() {
    const comp = useComponent();
    const { getAllActions, callOperation } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const state = useDomState(getState);
    const applyOperation = comp.env.editor.shared.history.makePreviewableAsyncOperation(
        (applySpecs) => {
            const proms = [];
            for (const applySpec of applySpecs) {
                proms.push(
                    applySpec.action.apply({
                        editingElement: applySpec.editingElement,
                        params: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadResult,
                        dependencyManager: comp.env.dependencyManager,
                    })
                );
            }
            return Promise.all(proms);
        }
    );
    function getState(editingElement) {
        // if (!editingElement || !editingElement.isConnected) {
        //     // TODO try to remove it. We need to move hook in BuilderComponent
        //     return {};
        // }
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        const actionValue = getAction(actionId).getValue({ editingElement, params: actionParam });
        return {
            selectedColor: actionValue || comp.props.defaultColor,
            selectedColorCombination: comp.env.editor.shared.color.getColorCombination(
                editingElement,
                actionParam
            ),
        };
    }
    function getColor(colorValue) {
        return colorValue.startsWith("color-prefix-")
            ? `var(${colorValue.replace("color-prefix-", "--")})`
            : colorValue;
    }

    let preventNextPreview = false;
    function onApply(colorValue) {
        preventNextPreview = false;
        callOperation(applyOperation.commit, { userInputValue: getColor(colorValue) });
    }
    let onPreview = (colorValue) => {
        // Avoid previewing the same color twice. It won't block previewing
        // another color, as in that case the mouseout/focusout will call an
        // explicit revert and set the flag to false.
        if (preventNextPreview) {
            return;
        }
        preventNextPreview = true;
        callOperation(applyOperation.preview, {
            preview: true,
            userInputValue: getColor(colorValue),
            operationParams: {
                cancellable: true,
                cancelPrevious: () => applyOperation.revert(),
            },
        });
    };
    const hasPreview = useHasPreview(getAllActions);
    if (!hasPreview) {
        onPreview = () => {};
    }
    return {
        state,
        onApply,
        onPreview,
        onPreviewRevert: () => {
            preventNextPreview = false;
            // The `next` will cancel the previous operation, which will revert
            // the operation in case of a preview.
            comp.env.editor.shared.operation.next();
        },
    };
}

export class BuilderColorPicker extends Component {
    static template = "html_builder.BuilderColorPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        noTransparency: { type: Boolean, optional: true },
        enabledTabs: { type: Array, optional: true },
        unit: { type: String, optional: true },
        title: { type: String, optional: true },
        getUsedCustomColors: { type: Function, optional: true },
        selectedTab: { type: String, optional: true },
        defaultColor: { type: String, optional: true },
    };
    static defaultProps = {
        enabledTabs: ["theme", "gradient", "custom"],
        defaultColor: "#FFFFFF00",
    };
    static components = {
        ColorSelector: ColorSelector,
        BuilderComponent,
    };

    setup() {
        useBuilderComponent();
        const { state, onApply, onPreview, onPreviewRevert } = useColorPickerBuilderComponent();
        this.colorButton = useRef("colorButton");
        this.state = state;
        this.state.defaultTab = this.props.selectedTab || "solid"; // TODO: select the correct tab based on the color
        useColorPicker(
            "colorButton",
            {
                state,
                applyColor: onApply,
                applyColorPreview: onPreview,
                applyColorResetPreview: onPreviewRevert,
                getUsedCustomColors:
                    this.props.getUsedCustomColors || this.getUsedCustomColors.bind(this),
                colorPrefix: "color-prefix-",
                themeColorPrefix: "hb-cp-",
                showRgbaField: true,
                noTransparency: this.props.noTransparency,
                enabledTabs: this.props.enabledTabs,
                className: "o-hb-colorpicker",
                editColorCombination: this.env.editColorCombination,
            },
            {
                onClose: onPreviewRevert,
                popoverClass: "o-hb-colorpicker-popover",
            }
        );
    }

    getSelectedColorStyle() {
        if (this.state.selectedColor) {
            if (isColorGradient(this.state.selectedColor)) {
                return `background-image: ${this.state.selectedColor}`;
            }
            return `background-color: ${this.state.selectedColor}`;
        }
        if (this.state.selectedColorCombination) {
            const colorCombination = this.state.selectedColorCombination.replace("_", "-");
            const el = this.env.getEditingElement();
            const style = el.ownerDocument.defaultView.getComputedStyle(el);
            if (style.backgroundImage !== "none") {
                return `background-image: ${style.backgroundImage}`;
            } else {
                return `background-color: var(--${colorCombination}-bg)`;
            }
        }
        return "";
    }

    getUsedCustomColors() {
        return getAllUsedColors(this.env.editor.editable);
    }
}
