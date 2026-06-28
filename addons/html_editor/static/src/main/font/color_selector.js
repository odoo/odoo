import { useChildEnv, useRef } from "@web/owl2/utils";
import { isColorGradient } from "@web/core/utils/colors";
import { Component, props, t, useEffect, proxy } from "@odoo/owl";
import {
    useColorPicker,
    DEFAULT_COLORS,
    DEFAULT_THEME_COLOR_VARS,
} from "@html_editor/components/color_picker/color_picker";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { useChildRef } from "@web/core/utils/hooks";
import { useDropdownAutoVisibility } from "@html_editor/toolbar_dropdown_hook";

export class ColorSelector extends Component {
    static template = "html_editor.ColorSelector";
    props = props({
        // from toolbarButtonProps
        title: t.or([t.string(), t.function()]),
        getSelection: t.function(),
        isDisabled: t.boolean(),
        mode: t.string(),
        type: t.string(),
        customIconClass: t.string().optional(),
        getSelectedColors: t.function(),
        applyColor: t.function(),
        applyColorPreview: t.function(),
        applyColorResetPreview: t.function(),
        getUsedCustomColors: t.function(),
        getTargetedElements: t.function(),
        colorPrefix: t.string(),
        enabledTabs: t.array().optional(["solid", "gradient", "custom"]),
        cssVarColorPrefix: t.string().optional(""),
        onClose: t.function(),
        useDefaultThemeColors: t.boolean().optional(true),
    });

    setup() {
        this.state = proxy({});
        this.colorSelectorState = proxy({ isOpen: false });
        const htmlStyle = getHtmlStyle(document);
        const defaultThemeColors = DEFAULT_THEME_COLOR_VARS.map((color) =>
            getCSSVariableValue(color, htmlStyle)
        );
        this.solidColors = [
            ...DEFAULT_COLORS.flat(),
            ...defaultThemeColors,
            getCSSVariableValue("body-color", htmlStyle), // Default applied color
            "#00000000", //Default Background color
        ];
        useEffect(() => {
            const selectedColors = this.props.getSelectedColors();
            this.state.selectedColor = selectedColors[this.props.mode];
            this.state.defaultTab = "solid";
            this.state.selectedTab = this.getCorrespondingColorTab(selectedColors[this.props.mode]);
            this.state.getTargetedElements = this.props.getTargetedElements;
        });

        const colorPickerRef = useChildRef();
        this.colorSelectorBtn = useRef("root");
        this.colorPicker = useColorPicker(
            "root",
            {
                state: this.state,
                applyColor: this.props.applyColor,
                applyColorPreview: this.props.applyColorPreview,
                applyColorResetPreview: this.props.applyColorResetPreview,
                getUsedCustomColors: this.props.getUsedCustomColors,
                colorPrefix: this.props.colorPrefix,
                enabledTabs: this.props.enabledTabs,
                cssVarColorPrefix: this.props.cssVarColorPrefix,
                useDefaultThemeColors: this.props.useDefaultThemeColors,
                onEscape: () => this.colorSelectorBtn.el?.focus(),
            },
            {
                env: useChildEnv(),
                onClose: (...args) => {
                    this.props.applyColorResetPreview();
                    this.props.onClose(...args);
                    this.colorSelectorState.isOpen = false;
                },
                onOpen: () => {
                    this.colorSelectorState.isOpen = true;
                },
                ref: colorPickerRef,
            }
        );
        useDropdownAutoVisibility(this.env.overlayState, colorPickerRef);
    }

    getCorrespondingColorTab(color) {
        if (!color || this.solidColors.includes(color.toUpperCase())) {
            return "solid";
        } else if (isColorGradient(color)) {
            return "gradient";
        } else {
            return "custom";
        }
    }

    getSelectedColorStyle() {
        if (isColorGradient(this.state.selectedColor)) {
            return `border-bottom: 2px solid transparent; border-image: ${this.state.selectedColor}; border-image-slice: 1`;
        }
        return `border-bottom: 2px solid ${
            this.state.selectedColor || this.props.getDefaultColor?.()
        }`;
    }
}
