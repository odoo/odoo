import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, useComponent, useRef } from "@odoo/owl";
import { useColorPicker } from "@web/core/color_picker/color_picker";
import { BuilderComponent } from "./builder_component";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDomState,
} from "./utils";
import { isColorGradient } from "@web/core/utils/colors";

// TODO replace by useInputBuilderComponent after extract unit by AGAU
export function useColorPickerBuilderComponent() {
    const comp = useComponent();
    const { getAllActions, callOperation } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const state = useDomState(getState);
    const applyOperation = comp.env.editor.shared.history.makePreviewableOperation((applySpecs) => {
        for (const applySpec of applySpecs) {
            let actionValue = applySpec.actionValue;
            if (actionValue.startsWith("color-prefix-")) {
                actionValue = `var(${actionValue.replace("color-prefix-", "--")})`;
            }
            applySpec.apply({
                editingElement: applySpec.editingElement,
                param: applySpec.actionParam,
                value: actionValue,
                loadResult: applySpec.loadResult,
                dependencyManager: comp.env.dependencyManager,
            });
        }
    });
    function getState(editingElement) {
        if (!editingElement || !editingElement.isConnected) {
            // TODO try to remove it. We need to move hook in BuilderComponent
            return {};
        }
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        const actionValue = getAction(actionId).getValue({ editingElement, param: actionParam });
        return {
            selectedColor: actionValue,
        };
    }

    function onApply(colorValue) {
        callOperation(applyOperation.commit, { userInputValue: colorValue });
    }
    let onPreview = (colorValue) => {
        callOperation(applyOperation.preview, {
            userInputValue: colorValue,
            operationParams: {
                cancellable: true,
                cancelPrevious: () => applyOperation.revert(),
            },
        });
    };
    if (
        comp.props.preview === false ||
        (comp.env.weContext.preview === false && comp.props.preview !== true)
    ) {
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
        unit: { type: String, optional: true },
        title: { type: String, optional: true },
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
        useColorPicker("colorButton", {
            state,
            applyColor: onApply,
            applyColorPreview: onPreview,
            applyColorResetPreview: onPreviewRevert,
            getUsedCustomColors: () => [],
            colorPrefix: "color-prefix-",
            noTransparency: this.props.noTransparency,
        });
    }

    getSelectedColorStyle() {
        if (isColorGradient(this.state.selectedColor)) {
            return `background-image: ${this.state.selectedColor}`;
        }
        return `background-color: ${this.state.selectedColor}`;
    }
}
