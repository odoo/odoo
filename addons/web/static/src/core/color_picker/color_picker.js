import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { CustomColorPicker } from "@web/core/color_picker/custom_color_picker/custom_color_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { isCSSColor, isColorGradient, normalizeCSSColor } from "@web/core/utils/colors";
import { cookie } from "@web/core/browser/cookie";
import { POSITION_BUS } from "../position/position_hook";
import { registry } from "../registry";

// These colors are already normalized as per normalizeCSSColor in @web/legacy/js/widgets/colorpicker
export const DEFAULT_COLORS = [
    ["#000000", "#424242", "#636363", "#9C9C94", "#CEC6CE", "#EFEFEF", "#F7F7F7", "#FFFFFF"],
    ["#FF0000", "#FF9C00", "#FFFF00", "#00FF00", "#00FFFF", "#0000FF", "#9C00FF", "#FF00FF"],
    ["#F7C6CE", "#FFE7CE", "#FFEFC6", "#D6EFD6", "#CEDEE7", "#CEE7F7", "#D6D6E7", "#E7D6DE"],
    ["#E79C9C", "#FFC69C", "#FFE79C", "#B5D6A5", "#A5C6CE", "#9CC6EF", "#B5A5D6", "#D6A5BD"],
    ["#E76363", "#F7AD6B", "#FFD663", "#94BD7B", "#73A5AD", "#6BADDE", "#8C7BC6", "#C67BA5"],
    ["#CE0000", "#E79439", "#EFC631", "#6BA54A", "#4A7B8C", "#3984C6", "#634AA5", "#A54A7B"],
    ["#9C0000", "#B56308", "#BD9400", "#397B21", "#104A5A", "#085294", "#311873", "#731842"],
    ["#630000", "#7B3900", "#846300", "#295218", "#083139", "#003163", "#21104A", "#4A1031"],
];

export const DEFAULT_GRAYSCALES = {
    solid: ["black", "900", "800", "600", "400", "200", "100", "white"],
};

// These CSS variables are defined in html_editor.
// Using ColorPicker without html_editor installed is extremely unlikely.
export const DEFAULT_THEME_COLOR_VARS = [
    "o-color-1",
    "o-color-2",
    "o-color-3",
    "o-color-4",
    "o-color-5",
];

export class ColorPicker extends Component {
    static template = "web.ColorPicker";
    static components = { CustomColorPicker };
    static props = {
        state: {
            type: Object,
            shape: {
                selectedColor: String,
                selectedColorCombination: { type: String, optional: true },
                getTargetedElements: { type: Function, optional: true },
                defaultTab: String,
                selectedTab: { type: String, optional: true },
                // todo: remove the `mode` prop in master
                mode: { type: String, optional: true },
            },
        },
        getUsedCustomColors: Function,
        applyColor: Function,
        applyColorPreview: Function,
        applyColorResetPreview: Function,
        editColorCombination: { type: Function, optional: true },
        setOnCloseCallback: { type: Function, optional: true },
        setOperationCallbacks: { type: Function, optional: true },
        enabledTabs: { type: Array, optional: true },
        colorPrefix: { type: String },
        cssVarColorPrefix: { type: String, optional: true },
        defaultOpacity: { type: Number, optional: true },
        grayscales: { type: Object, optional: true },
        noTransparency: { type: Boolean, optional: true },
        close: { type: Function, optional: true },
        className: { type: String, optional: true },
    };
    static defaultProps = {
        close: () => {},
        defaultOpacity: 100,
        enabledTabs: ["solid", "custom"],
        cssVarColorPrefix: "",
        setOnCloseCallback: () => {},
    };

    setup() {
        this.tabs = registry
            .category("color_picker_tabs")
            .getAll()
            .filter((tab) => this.props.enabledTabs.includes(tab.id));
        this.root = useRef("root");

        this.DEFAULT_COLORS = DEFAULT_COLORS;
        this.grayscales = Object.assign({}, DEFAULT_GRAYSCALES, this.props.grayscales);
        this.DEFAULT_THEME_COLOR_VARS = DEFAULT_THEME_COLOR_VARS;
        this.defaultColorSet = this.getDefaultColorSet();
        this.defaultColor = this.props.state.selectedColor;
        this.focusedBtn = null;
        this.onApplyCallback = () => {};
        this.onPreviewRevertCallback = () => {};
        this.getPreviewColor = () => {};

        this.state = useState({
            activeTab: this.props.state.selectedTab || this.getDefaultTab(),
            currentCustomColor: this.props.state.selectedColor,
            currentColorPreview: undefined,
            showGradientPicker: false,
        });
        this.usedCustomColors = this.props.getUsedCustomColors();
        useEffect(
            () => {
                // Recompute the positioning of the popover if any.
                this.env[POSITION_BUS]?.trigger("update");
            },
            () => [this.state.activeTab]
        );
    }

    getDefaultTab() {
        if (this.props.enabledTabs.includes(this.props.state.defaultTab)) {
            return this.props.state.defaultTab;
        }
        return this.props.enabledTabs[0];
    }

    get selectedColor() {
        return this.props.state.selectedColor;
    }

    get isDarkTheme() {
        return cookie.get("color_scheme") === "dark";
    }

    setTab(tab) {
        this.state.activeTab = tab;
        // Reset the preview revert callback, as it is tab-specific.
        this.setOperationCallbacks({ onPreviewRevertCallback: () => {} });
        this.applyColorResetPreview();
    }

    processColorFromEvent(ev) {
        const target = this.getTarget(ev);
        let color = target.dataset.color || "";
        if (color && isColorCombination(color)) {
            return color;
        }
        if (color && !isCSSColor(color) && !isColorGradient(color)) {
            color = this.props.colorPrefix + color;
        }
        return color;
    }
    /**
     * @param {Object} cbs - callbacks
     * @param {Function} cbs.onApplyCallback
     * @param {Function} cbs.onPreviewRevertCallback
     */
    setOperationCallbacks(cbs) {
        // The gradient colorpicker has a nested ColorPicker. We need to use the
        // `setOperationCallbacks` from the parent ColorPicker for it to be
        // impacted.
        if (this.props.setOperationCallbacks) {
            this.props.setOperationCallbacks(cbs);
        }
        if (cbs.onApplyCallback) {
            this.onApplyCallback = cbs.onApplyCallback;
        }
        if (cbs.onPreviewRevertCallback) {
            this.onPreviewRevertCallback = cbs.onPreviewRevertCallback;
        }
        if (cbs.getPreviewColor) {
            this.getPreviewColor = cbs.getPreviewColor;
        }
    }

    applyColor(color) {
        this.state.currentCustomColor = color;
        this.props.applyColor(color);
        this.defaultColorSet = this.getDefaultColorSet();
        this.onApplyCallback();
    }

    onColorApply(ev) {
        if (!this.isColorButton(this.getTarget(ev))) {
            return;
        }
        const color = this.processColorFromEvent(ev);
        this.applyColor(color);
        this.props.close();
    }

    applyColorResetPreview() {
        this.props.applyColorResetPreview();
        this.state.currentColorPreview = undefined;
        this.onPreviewRevertCallback();
    }

    onColorPreview(ev) {
        const color = ev.hex || ev.gradient || this.processColorFromEvent(ev);
        this.props.applyColorPreview(color);
        this.state.currentColorPreview = this.getPreviewColor();
    }

    onColorHover(ev) {
        if (!this.isColorButton(this.getTarget(ev))) {
            return;
        }
        this.onColorPreview(ev);
    }

    onColorHoverOut(ev) {
        if (!this.isColorButton(this.getTarget(ev))) {
            return;
        }
        this.applyColorResetPreview();
    }
    getTarget(ev) {
        const target = ev.target.closest(`[data-color]`);
        return this.root.el.contains(target) ? target : ev.target;
    }

    onColorFocusin(ev) {
        // In the editor color picker, the preview and reset reapply the
        // selection, which can remove the focus from the current button (if the
        // node is recreated). We need to force the focus and break the infinite
        // loop that it could trigger.
        if (this.focusedBtn === ev.target) {
            this.focusedBtn = null;
            return;
        }
        this.focusedBtn = ev.target;
        this.onColorHover(ev);
        if (document.activeElement !== ev.target) {
            // The focus was lost during revert. Reset it where it should be.
            ev.target.focus();
        }
    }

    onColorFocusout(ev) {
        if (!ev.relatedTarget || !this.isColorButton(ev.relatedTarget)) {
            // Do not trigger a revert if we are in the focus loop (i.e. focus
            // a button > selection is reset > focusout). Otherwise, the
            // relatedTarget should always be one of the colorpicker's buttons.
            return;
        }
        const activeEl = document.activeElement;
        this.applyColorResetPreview();
        if (document.activeElement !== activeEl) {
            // The focus was lost during revert. Reset it where it should be.
            ev.relatedTarget.focus();
        }
    }

    getDefaultColorSet() {
        if (!this.props.state.selectedColor) {
            return;
        }
        let defaultColors = this.props.enabledTabs.includes("solid")
            ? this.DEFAULT_THEME_COLOR_VARS
            : [];
        for (const grayscale of Object.values(this.grayscales)) {
            defaultColors = defaultColors.concat(grayscale);
        }

        const targetedElement =
            this.props.state.getTargetedElements?.()[0] || document.documentElement;
        const selectedColor = this.props.state.selectedColor.toUpperCase();
        const htmlStyle =
            targetedElement.ownerDocument.defaultView.getComputedStyle(targetedElement);

        for (const color of defaultColors) {
            const cssVar = normalizeCSSColor(htmlStyle.getPropertyValue(`--${color}`));
            if (cssVar?.toUpperCase() === selectedColor) {
                return color;
            }
        }

        return false;
    }

    colorPickerNavigation(ev) {
        const { target, key } = ev;
        if (!target.classList.contains("o_color_button")) {
            return;
        }
        if (!["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown"].includes(key)) {
            return;
        }

        let targetBtn;
        if (key === "ArrowRight") {
            targetBtn = target.nextElementSibling;
        } else if (key === "ArrowLeft") {
            targetBtn = target.previousElementSibling;
        } else if (key === "ArrowUp" || key === "ArrowDown") {
            const buttonIndex = [...target.parentElement.children].indexOf(target);
            const nbColumns = getComputedStyle(target).getPropertyValue(
                "--o-color-picker-grid-columns"
            );
            targetBtn =
                target.parentElement.children[
                    buttonIndex + (key === "ArrowUp" ? -1 : 1) * nbColumns
                ];
            if (!targetBtn) {
                const row =
                    key === "ArrowUp"
                        ? target.parentElement.previousElementSibling
                        : target.parentElement.nextElementSibling;
                if (row?.matches(".o_color_section, .o_colorpicker_section")) {
                    targetBtn = row.children[buttonIndex];
                }
            }
        }
        if (targetBtn && targetBtn.classList.contains("o_color_button")) {
            targetBtn.focus();
        }
    }

    isColorButton(targetEl) {
        return targetEl.tagName === "BUTTON" && !targetEl.matches(".o_colorpicker_ignore");
    }
}

export function useColorPicker(refName, props, options = {}) {
    // Callback to be overridden by child components (e.g. custom color picker).
    let onCloseCallback = () => {};
    const setOnCloseCallback = (cb) => {
        onCloseCallback = cb;
    };
    props.setOnCloseCallback = setOnCloseCallback;
    if (options.onClose) {
        const onClose = options.onClose;
        options.onClose = () => {
            onCloseCallback();
            onClose();
        };
    }

    const colorPicker = usePopover(ColorPicker, options);
    const root = useRef(refName);

    function onClick() {
        colorPicker.isOpen ? colorPicker.close() : colorPicker.open(root.el, props);
    }

    useEffect(
        (el) => {
            if (!el) {
                return;
            }
            el.addEventListener("click", onClick);
            return () => {
                el.removeEventListener("click", onClick);
            };
        },
        () => [root.el]
    );

    return colorPicker;
}

/**
 * Checks if a given string is a color combination.
 *
 * @param {string} color
 * @returns {boolean}
 */
function isColorCombination(color) {
    return color.startsWith("o_cc");
}
