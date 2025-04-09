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
import { COLOR_COMBINATION_CLASSES_REGEX } from "@html_editor/utils/color";

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
                    applySpec.apply({
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
            selectedColor: actionValue || "#FFFFFF00",
            selectedColorCombination: getColorCombination(editingElement),
        };
    }
    function getColor(colorValue) {
        return colorValue.startsWith("color-prefix-")
            ? `var(${colorValue.replace("color-prefix-", "--")})`
            : colorValue;
    }

    function onApply(colorValue) {
        callOperation(applyOperation.commit, { userInputValue: getColor(colorValue) });
    }
    let onPreview = (colorValue) => {
        callOperation(applyOperation.preview, {
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
        onPreviewRevert: () => applyOperation.revert(),
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
    };
    static defaultProps = {
        getUsedCustomColors: () => [],
        enabledTabs: ["theme", "gradient", "custom"],
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
                getUsedCustomColors: this.props.getUsedCustomColors,
                colorPrefix: "color-prefix-",
                noTransparency: this.props.noTransparency,
                enabledTabs: this.props.enabledTabs,
            },
            {
                onClose: onPreviewRevert,
            }
        );
    }

    getSelectedColorStyle() {
        if (isColorGradient(this.state.selectedColor)) {
            return `background-image: ${this.state.selectedColor}`;
        }
        return `background-color: ${this.state.selectedColor}`;
    }
}

function getColorCombination(el) {
    return el.className.match?.(COLOR_COMBINATION_CLASSES_REGEX)?.[0];
}
