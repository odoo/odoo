import { getAllUsedColors } from "@html_builder/utils/utils_css";
import {
    DEFAULT_COLORS,
    DEFAULT_THEME_COLOR_VARS,
    useColorPicker,
} from "@html_editor/components/color_picker/color_picker";
import { ColorSelector } from "@html_editor/main/font/color_selector";
import { Component, signal, t, useProps } from "@odoo/owl";
import { isCSSColor, isColorGradient } from "@web/core/utils/colors";
import { useEnv } from "@web/owl2/utils";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    hasPreview,
    revertPreview,
    useBuilderComponent,
    useDomState,
} from "../utils";
import { BuilderComponent } from "./builder_component";

// TODO replace by useInputBuilderComponent after extract unit by AGAU
function useColorPickerBuilderComponent(props) {
    const env = useEnv();
    const { getAllActions, callOperation } = getAllActionsAndOperations(props);
    const getAction = env.editor.shared.builderActions.getAction;
    let selectedTab;
    const state = useDomState(getState);
    const applyOperation = env.editor.shared.history.makePreviewableAsyncOperation(
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
                        dependencyManager: env.dependencyManager,
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
            defaultTab: props.selectedTab,
            selectedColor: actionValue || props.defaultColor,
            selectedColorCombination: env.editor.shared.color.getColorCombination(
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

    function getCorrespondingColorPickerTab(selectedColor) {
        if (!selectedColor) {
            return;
        }

        selectedColor = selectedColor.replaceAll(/color-prefix-/g, "");
        const isTabEnabled = (tab) => props.enabledTabs.includes(tab);

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

    let previewValue = null;
    function onApply(colorValue) {
        previewValue = null;
        selectedTab = getCorrespondingColorPickerTab(colorValue);
        callOperation(applyOperation.commit, { userInputValue: getColor(colorValue) });
    }
    function onPreview(colorValue) {
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
    }
    return {
        state,
        onApply,
        onPreview: hasPreview(props, getAllActions) ? onPreview : () => {},
        onPreviewRevert: () => {
            previewValue = null;
            revertPreview(env.editor);
        },
    };
}

export class ColorPickerButton extends Component {
    static template = "html_builder.ColorPickerButton";

    props = useProps({
        title: t.string().optional(),
        style: t.string(),
        tooltip: t.string().optional(),
        colorPickerConfig: t.object({
            props: t.object(),
            options: t.object(),
        }),
    });

    colorButtonRef = signal.ref();

    setup() {
        useColorPicker(
            this.colorButtonRef,
            this.props.colorPickerConfig.props,
            this.props.colorPickerConfig.options
        );
    }
}

export class BuilderColorPicker extends Component {
    static components = {
        ColorSelector: ColorSelector,
        BuilderComponent,
        ColorPickerButton,
    };
    static template = "html_builder.BuilderColorPicker";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        noTransparency: t.boolean().optional(),
        enabledTabs: t.array().optional(["theme", "gradient", "custom"]),
        grayscales: t.object().optional(),
        unit: t.string().optional(),
        title: t.string().optional(),
        tooltip: t.string().optional(),
        getUsedCustomColors: t.function().optional(),
        selectedTab: t.string().optional("theme"),
        defaultColor: t.string().optional("#FFFFFF00"),
        defaultOpacity: t.number().optional(),
        colorPickerClassName: t.string().optional("o-hb-colorpicker"),
        colorPickerPopoverClassName: t.string().optional("o-hb-colorpicker-popover"),
    });

    setup() {
        useBuilderComponent(this.props);
        const { state, onApply, onPreview, onPreviewRevert } = useColorPickerBuilderComponent(
            this.props
        );
        this.state = state;

        this.colorPickerConfig = {
            props: {
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
                className: this.props.colorPickerClassName,
                editColorCombination: this.env.editColorCombination,
            },
            options: {
                onClose: onPreviewRevert,
                popoverClass: this.props.colorPickerPopoverClassName,
            },
        };
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
            return `background-color: var(--hb-cp-${colorCombination}-bg); background-image: var(--hb-cp-${colorCombination}-bg-gradient);`;
        }
        return "";
    }

    getUsedCustomColors() {
        return getAllUsedColors(this.env.editor.editable);
    }
}
