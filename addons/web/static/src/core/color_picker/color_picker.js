import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { CustomColorPicker } from "@web/core/color_picker/custom_color_picker/custom_color_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { isCSSColor, isColorGradient } from "@web/core/utils/colors";
import { GradientPicker } from "./gradient_picker/gradient_picker";

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

export const DEFAULT_THEME_COLOR_VARS = [
    "o-color-1",
    "o-color-2",
    "o-color-3",
    "o-color-4",
    "o-color-5",
];

const DEFAULT_COLOR = "#FF0000";

export class ColorPicker extends Component {
    static template = "web.ColorPicker";
    static components = { CustomColorPicker, GradientPicker };
    static props = {
        state: {
            type: Object,
            shape: {
                selectedColor: String,
                defaultTab: String,
            },
        },
        getUsedCustomColors: Function,
        applyColor: Function,
        applyColorPreview: Function,
        applyColorResetPreview: Function,
        colorPrefix: { type: String },
        close: { type: Function, optional: true },
    };
    static defaultProps = {
<<<<<<< 9df334c0aca8a57dcbed4c87b43b18403f3a7c6e
        close: () => {},
||||||| b8c55ff9da25ccfc84d0e588aa790d0080cc8a55
        document: window.document,
        defaultColor: "#FF0000",
        noTransparency: false,
        stopClickPropagation: false,
        onColorSelect: () => {},
        onColorPreview: () => {},
        onInputEnter: () => {},
=======
        document: window.document,
        defaultColor: DEFAULT_COLOR,
        noTransparency: false,
        stopClickPropagation: false,
        onColorSelect: () => {},
        onColorPreview: () => {},
        onInputEnter: () => {},
>>>>>>> 2bdeb18cf3cc3744a382fb402229e58ac9dd0059
    };

    setup() {
        this.DEFAULT_COLORS = DEFAULT_COLORS;
        this.DEFAULT_GRADIENT_COLORS = DEFAULT_GRADIENT_COLORS;

<<<<<<< 9df334c0aca8a57dcbed4c87b43b18403f3a7c6e
        this.defaultColor = this.props.state.selectedColor;
        this.state = useState({
            activeTab: this.props.state.defaultTab,
            currentCustomColor: this.props.state.selectedColor,
            showGradientPicker: false,
||||||| b8c55ff9da25ccfc84d0e588aa790d0080cc8a55
        this.debouncedOnChangeInputs = debounce(this.onChangeInputs.bind(this), 10, true);

        this.elRef = useRef("el");
        this.colorPickerAreaRef = useRef("colorPickerArea");
        this.colorPickerPointerRef = useRef("colorPickerPointer");
        this.colorSliderRef = useRef("colorSlider");
        this.colorSliderPointerRef = useRef("colorSliderPointer");
        this.opacitySliderRef = useRef("opacitySlider");
        this.opacitySliderPointerRef = useRef("opacitySliderPointer");

        // Need to be bound on all documents to work in all possible cases (we
        // have to be able to start dragging/moving from the colorpicker to
        // anywhere on the screen, crossing iframes).
        const documents = [
            window.top,
            ...Array.from(window.top.frames).filter((frame) => {
                try {
                    const document = frame.document;
                    return !!document;
                } catch {
                    // We cannot access the document (cross origin).
                    return false;
                }
            }),
        ].map((w) => w.document);
        this.throttleOnMouseMove = useThrottleForAnimation((ev) => {
            this.onMouseMovePicker(ev);
            this.onMouseMoveSlider(ev);
            this.onMouseMoveOpacitySlider(ev);
        });

        for (const doc of documents) {
            useExternalListener(doc, "mousemove", this.throttleOnMouseMove);
            useExternalListener(doc, "mouseup", this.onMouseUp.bind(this));
        }
        onMounted(async () => {
            const defaultCssColor = this.props.selectedColor
                ? this.props.selectedColor
                : this.props.defaultColor;
            const rgba = convertCSSColorToRgba(defaultCssColor);
            if (rgba) {
                this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);
            }

            this.previewActive = true;
            this._updateUI();
        });
        onWillUpdateProps((newProps) => {
            const newSelectedColor = newProps.selectedColor
                ? newProps.selectedColor
                : newProps.defaultColor;
            this.setSelectedColor(newSelectedColor);
=======
        this.debouncedOnChangeInputs = debounce(this.onChangeInputs.bind(this), 10, true);

        this.elRef = useRef("el");
        this.colorPickerAreaRef = useRef("colorPickerArea");
        this.colorPickerPointerRef = useRef("colorPickerPointer");
        this.colorSliderRef = useRef("colorSlider");
        this.colorSliderPointerRef = useRef("colorSliderPointer");
        this.opacitySliderRef = useRef("opacitySlider");
        this.opacitySliderPointerRef = useRef("opacitySliderPointer");

        // Need to be bound on all documents to work in all possible cases (we
        // have to be able to start dragging/moving from the colorpicker to
        // anywhere on the screen, crossing iframes).
        const documents = [
            window.top,
            ...Array.from(window.top.frames).filter((frame) => {
                try {
                    const document = frame.document;
                    return !!document;
                } catch {
                    // We cannot access the document (cross origin).
                    return false;
                }
            }),
        ].map((w) => w.document);
        this.throttleOnMouseMove = useThrottleForAnimation((ev) => {
            this.onMouseMovePicker(ev);
            this.onMouseMoveSlider(ev);
            this.onMouseMoveOpacitySlider(ev);
        });

        for (const doc of documents) {
            useExternalListener(doc, "mousemove", this.throttleOnMouseMove);
            useExternalListener(doc, "mouseup", this.onMouseUp.bind(this));
        }
        onMounted(async () => {
            const defaultCssColor = this.props.selectedColor
                ? this.props.selectedColor
                : this.props.defaultColor;
            const rgba =
                convertCSSColorToRgba(defaultCssColor) || convertCSSColorToRgba(DEFAULT_COLOR);
            if (rgba) {
                this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);
            }

            this.previewActive = true;
            this._updateUI();
        });
        onWillUpdateProps((newProps) => {
            const newSelectedColor = newProps.selectedColor
                ? newProps.selectedColor
                : newProps.defaultColor;
            this.setSelectedColor(newSelectedColor);
>>>>>>> 2bdeb18cf3cc3744a382fb402229e58ac9dd0059
        });
        this.usedCustomColors = this.props.getUsedCustomColors();
    }

    get selectedColor() {
        return this.props.state.selectedColor;
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    processColorFromEvent(ev) {
        let color = ev.target.dataset.color || "";
        if (color && !isCSSColor(color) && !isColorGradient(color)) {
            color = this.props.colorPrefix + color;
        }
        return color;
    }

    applyColor(color) {
        this.state.currentCustomColor = color;
        this.props.applyColor(color);
    }

    onColorApply(ev) {
        if (ev.target.tagName !== "BUTTON") {
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

    onColorHover(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        this.onColorPreview(ev);
    }

    onColorHoverOut(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        this.props.applyColorResetPreview();
    }

    getCurrentGradientColor() {
        if (isColorGradient(this.props.state.selectedColor)) {
            return this.props.state.selectedColor;
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

        let targetBtn;
        if (key === "ArrowRight") {
            targetBtn = target.nextElementSibling;
        } else if (key === "ArrowLeft") {
            targetBtn = target.previousElementSibling;
        } else if (key === "ArrowUp" || key === "ArrowDown") {
            const buttonIndex = [...target.parentElement.children].indexOf(target);
            const row =
                key === "ArrowUp"
                    ? target.parentElement.previousElementSibling
                    : target.parentElement.nextElementSibling;
            if (row?.matches(".o_color_section, .o_colorpicker_section")) {
                targetBtn = row.children[buttonIndex];
            }
        }
        if (targetBtn?.classList.contains("o_color_button")) {
            targetBtn.focus();
        }
    }
}

export function useColorPicker(refName, props, options = {}) {
    const colorPicker = usePopover(ColorPicker, options);
    const root = useRef(refName);

    function onClick() {
        colorPicker.open(root.el, props);
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
