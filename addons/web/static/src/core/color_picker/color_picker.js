import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { CustomColorPicker } from "@web/core/color_picker/custom_color_picker/custom_color_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { applyOpacityToGradient, isCSSColor, isColorGradient } from "@web/core/utils/colors";
import { cookie } from "@web/core/browser/cookie";
import { GradientPicker } from "./gradient_picker/gradient_picker";
import { POSITION_BUS } from "../position/position_hook";

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

const DEFAULT_GRADIENT_COLORS = [
    "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)",
    "linear-gradient(135deg, rgb(102, 153, 255) 0%, rgb(255, 51, 102) 100%)",
    "linear-gradient(135deg, rgb(47, 128, 237) 0%, rgb(178, 255, 218) 100%)",
    "linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)",
    "linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%)",
    "linear-gradient(135deg, rgb(255, 222, 69) 0%, rgb(69, 33, 0) 100%)",
    "linear-gradient(135deg, rgb(222, 222, 222) 0%, rgb(69, 69, 69) 100%)",
    "linear-gradient(135deg, rgb(255, 222, 202) 0%, rgb(202, 115, 69) 100%)",
];

const DEFAULT_GRAYSCALES = {
    solid: ["black", "900", "800", "600", "400", "200", "100", "white"],
};

export const DEFAULT_THEME_COLOR_VARS = [
    "o-color-1",
    "o-color-2",
    "o-color-3",
    "o-color-4",
    "o-color-5",
];

export class ColorPicker extends Component {
    static template = "web.ColorPicker";
    static components = { CustomColorPicker, GradientPicker };
    static props = {
        state: {
            type: Object,
            shape: {
                selectedColor: String,
                selectedColorCombination: { type: String, optional: true },
                getTargetedElements: { type: Function, optional: true },
                defaultTab: String,
                mode: { type: String, optional: true },
            },
        },
        getUsedCustomColors: Function,
        applyColor: Function,
        applyColorPreview: Function,
        applyColorResetPreview: Function,
        editColorCombination: { type: Function, optional: true },
        enabledTabs: { type: Array, optional: true },
        colorPrefix: { type: String },
        themeColorPrefix: { type: String, optional: true },
        showRgbaField: { type: Boolean, optional: true },
        defaultOpacity: { type: Number, optional: true },
        grayscales: { type: Object, optional: true },
        noTransparency: { type: Boolean, optional: true },
        close: { type: Function, optional: true },
        className: { type: String, optional: true },
    };
    static defaultProps = {
        close: () => {},
        defaultOpacity: 100,
        enabledTabs: ["solid", "gradient", "custom"],
        showRgbaField: false,
        themeColorPrefix: "",
    };
    applyOpacityToGradient = applyOpacityToGradient;

    setup() {
        this.DEFAULT_COLORS = DEFAULT_COLORS;
        this.DEFAULT_GRADIENT_COLORS = DEFAULT_GRADIENT_COLORS;
        this.grayscales = Object.assign({}, DEFAULT_GRAYSCALES);
        this.grayscales = Object.assign(this.grayscales, this.props.grayscales);
        this.DEFAULT_THEME_COLOR_VARS = DEFAULT_THEME_COLOR_VARS;
        this.defaultColorSet = this.getDefaultColorSet();
        this.root = useRef("root");

        this.defaultColor = this.props.state.selectedColor;
        this.focusedBtn = null;
        this.state = useState({
            activeTab: this.getDefaultTab(),
            currentCustomColor: this.props.state.selectedColor,
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

    applyColor(color) {
        this.state.currentCustomColor = color;
        this.props.applyColor(color);
        this.defaultColorSet = this.getDefaultColorSet();
    }

    onColorApply(ev) {
        if (!this.isColorButton(this.getTarget(ev))) {
            return;
        }
        const color = this.processColorFromEvent(ev);
        this.applyColor(color);
        this.props.close();
    }

    onColorPreview(ev) {
        const color = ev.hex ? ev.hex : this.processColorFromEvent(ev);
        this.props.applyColorPreview(color);
    }

    onCustomColorPreview(ev) {
        this.props.applyColorResetPreview();
        this.onColorPreview(ev);
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
        this.props.applyColorResetPreview();
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
        this.props.applyColorResetPreview();
        if (document.activeElement !== activeEl) {
            // The focus was lost during revert. Reset it where it should be.
            ev.relatedTarget.focus();
        }
    }

    getCurrentGradientColor() {
        if (isColorGradient(this.props.state.selectedColor)) {
            return this.props.state.selectedColor;
        }
    }

    getDefaultColorSet() {
        if (!this.props.state.getTargetedElements || !this.props.state.mode) {
            return;
        }
        const targetedEls = this.props.state.getTargetedElements();
        let defaultColors = this.props.enabledTabs.includes("solid")
            ? this.DEFAULT_THEME_COLOR_VARS
            : [];
        for (const grayscale of Object.values(this.grayscales)) {
            defaultColors = defaultColors.concat(grayscale);
        }

        const extractColorFromClasses = (targetedEls, prefix, defaultColors) => {
            for (const el of targetedEls) {
                for (const className of el.classList) {
                    const match = className.match(new RegExp(`^${prefix}-(.+)$`));
                    if (match && defaultColors.includes(match[1])) {
                        return match[1];
                    }
                }
            }
            return false;
        };
        switch (this.props.state.mode) {
            case "color":
                return extractColorFromClasses(targetedEls, "text", defaultColors);
            case "background-color":
            case "backgroundColor":
                return extractColorFromClasses(targetedEls, "bg", defaultColors);
            case "selectFilterColor": {
                const filterEls = targetedEls
                    .map((el) => el.querySelector(".o_we_bg_filter"))
                    .filter((el) => el !== null);
                return extractColorFromClasses(filterEls, "bg", defaultColors);
            }
            default: {
                for (const el of targetedEls) {
                    const color = el.dataset[this.props.state.mode];
                    if (
                        defaultColors.includes(color) ||
                        defaultColors.includes(this.props.state.mode)
                    ) {
                        return color;
                    }
                }
                return false;
            }
        }
    }
    toggleGradientPicker() {
        this.state.showGradientPicker = !this.state.showGradientPicker;
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
