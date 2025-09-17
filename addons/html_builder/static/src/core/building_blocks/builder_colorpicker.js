import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, useComponent, useRef } from "@odoo/owl";
import {
    useColorPicker,
    DEFAULT_COLORS,
    DEFAULT_THEME_COLOR_VARS,
} from "@web/core/color_picker/color_picker";
import { BuilderComponent } from "./builder_component";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDomState,
    useHasPreview,
} from "../utils";
import { isCSSColor, isColorGradient } from "@web/core/utils/colors";
import { getAllUsedColors } from "@html_builder/utils/utils_css";

// TODO replace by useInputBuilderComponent after extract unit by AGAU
export function useColorPickerBuilderComponent() {
    const comp = useComponent();
    const { getAllActions, callOperation } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    let selectedTab;
    const state = useDomState(getState);
    const applyOperation = comp.env.editor.shared.history.makePreviewableAsyncOperation(
        (applySpecs, isPreviewing) => {
            const proms = [];
            for (const applySpec of applySpecs) {
                proms.push(
                    applySpec.action.apply({
                        isPreviewing,
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
            // defaultTab is the tab to open if the user has not done a selection yet.
            // If the user has already selected a color, the tab of the last selection is opened
            defaultTab: comp.props.selectedTab,
            mode: actionParam.mainParam || actionId,
            selectedColor: actionValue || comp.props.defaultColor,
            selectedColorCombination: comp.env.editor.shared.color.getColorCombination(
                editingElement,
                actionParam
            ),
            getTargetedElements: () => [editingElement],
            selectedTab,
        };
    }
    function getColor(colorValue) {
        return colorValue.startsWith("color-prefix-")
            ? `var(${colorValue.replace("color-prefix-", "--")})`
            : colorValue;
    }

    let previewValue = null;
    function onApply(colorValue) {
        previewValue = null;
        selectedTab = comp.getCorrespondingColorPickerTab(colorValue);
        callOperation(applyOperation.commit, { userInputValue: getColor(colorValue) });
    }
    let onPreview = (colorValue) => {
        // Avoid previewing the same color twice.
        if (previewValue === colorValue) {
            return;
        }
        previewValue = colorValue;
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
            previewValue = null;
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
        grayscales: { type: Object, optional: true },
        unit: { type: String, optional: true },
        title: { type: String, optional: true },
        getUsedCustomColors: { type: Function, optional: true },
        selectedTab: { type: String, optional: true },
        defaultColor: { type: String, optional: true },
        defaultOpacity: { type: Number, optional: true },
    };
    static defaultProps = {
        enabledTabs: ["theme", "gradient", "custom"],
        defaultColor: "#FFFFFF00",
        selectedTab: "theme",
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
                cssVarColorPrefix: "hb-cp-",
                noTransparency: this.props.noTransparency,
                enabledTabs: this.props.enabledTabs,
                grayscales: this.props.grayscales,
                defaultOpacity: this.props.defaultOpacity,
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
            if (isCSSColor(this.state.selectedColor)) {
                return `background-color: ${this.state.selectedColor}`;
            }
            return `background-color: var(--${this.state.selectedColor})`;
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

    getCorrespondingColorPickerTab(selectedColor) {
        if (!selectedColor) {
            return;
        }

        selectedColor = selectedColor.replace(/color-prefix-/g, "");
        const isTabEnabled = (tab) => this.props.enabledTabs.includes(tab);

        if (isTabEnabled("gradient") && isColorGradient(selectedColor)) {
            return "gradient";
        }

        const solidTabColors = [
            ...DEFAULT_COLORS.flat(),
            ...DEFAULT_THEME_COLOR_VARS.map((color) => color.toUpperCase()),
        ];
        if (isTabEnabled("solid") && solidTabColors.includes(selectedColor.toUpperCase())) {
            return "solid";
        }

        if (isTabEnabled("theme") && /^o_cc\d+$/.test(selectedColor)) {
            return "theme";
        }

        if (isTabEnabled("custom")) {
            return "custom";
        }
    }
}
