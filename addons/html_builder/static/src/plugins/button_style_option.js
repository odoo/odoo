import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { BuilderColorPicker } from "@html_builder/core/building_blocks/builder_colorpicker";
import { BuilderSelect } from "@html_builder/core/building_blocks/builder_select";
import { BuilderSelectItem } from "@html_builder/core/building_blocks/builder_select_item";
import { BuilderNumberInput } from "@html_builder/core/building_blocks/builder_number_input";
import { BuilderAction } from "@html_builder/core/builder_action";
import { StyleAction, withoutTransition } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    convertCSSColorToRgba,
    convertRgbaToCSSColor,
    getContrastingColor,
    mixCssColors,
    normalizeCSSColor,
} from "@web/core/utils/colors";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import {
    BUTTON_SHAPES,
    BUTTON_SIZES,
    BUTTON_TYPES,
    computeButtonClasses,
    getButtonShape,
    getButtonSize,
    getButtonType,
} from "@html_editor/utils/button_style";

const HOVER_BG_MIX_AMOUNT = 0.15;

function updateCustomHoverBackground(el) {
    const bgColor = el.ownerDocument.defaultView.getComputedStyle(el).backgroundColor;
    const rgba = convertCSSColorToRgba(bgColor);
    if (!rgba || !rgba.opacity) {
        el.style.removeProperty("--btn-custom-hover-bg");
        return;
    }
    const mixColor = getContrastingColor(bgColor) === "#FFFFFF" ? "#000000" : "#FFFFFF";
    const hoverRgba = convertCSSColorToRgba(
        mixCssColors(bgColor, mixColor, 1 - HOVER_BG_MIX_AMOUNT)
    );
    el.style.setProperty(
        "--btn-custom-hover-bg",
        convertRgbaToCSSColor(hoverRgba.red, hoverRgba.green, hoverRgba.blue, rgba.opacity)
    );
}

export class ButtonStyleOptionPlugin extends Plugin {
    static id = "buttonStyleOption";
    resources = {
        builder_actions: {
            ButtonStyleAction,
            ButtonFillColorAction,
            ButtonColorAction,
        },
    };
}

export class ButtonStyleOption extends BaseOptionComponent {
    static id = "button_style_option";
    static template = "html_builder.ButtonStyleOption";
    static components = {
        BuilderColorPicker,
        BuilderSelect,
        BuilderSelectItem,
        BuilderNumberInput,
        BorderConfigurator,
    };
    static dependencies = ["domObserver"];
    static cleanForSave = (editingEl) => {
        if (!editingEl.matches(".btn-custom, .btn-fill-custom, .btn-outline-custom")) {
            editingEl.style.removeProperty("--btn-custom-color");
            editingEl.style.removeProperty("--btn-custom-hover-bg");
        }
    };

    buttonSizesData = BUTTON_SIZES;
    buttonShapesData = BUTTON_SHAPES;
    buttonTypesData = BUTTON_TYPES;

    setup() {
        super.setup();
        this.state = useDomState(async (el) => {
            const currentButtonType = getButtonType(el);
            const currentButtonShape = getButtonShape(el);
            const buttonStyles = await this.getButtonStyles(el);
            const hasAlpha = this.getHasAlpha(buttonStyles);
            const state = {
                buttonStyles,
                buttonCombinationClass: this.findColorCombination(el),
                currentButtonType,
                currentButtonTypeData: this.buttonTypesData.find(
                    (btn) => btn.type == currentButtonType
                ),
                currentButtonShape,
                currentButtonShapeData: this.buttonShapesData.find(
                    (btn) => btn.shape == currentButtonShape
                ),
                isOutline: currentButtonShape.startsWith("outline"),
                hasAlpha,
            };
            return state;
        });
    }

    goToThemeTab() {
        this.env.editColorCombination(
            parseInt(this.state.buttonCombinationClass.replace("o_cc", ""))
        );
    }

    async getButtonStyles(el) {
        // Button variant styles depend on user-customized theme settings
        // and on where the builder is running (website or mass mailing). The
        // cleanest approach to generate a preview is to add a temporary button
        // to the DOM and copy its computed styles. See commit message for more.
        const buttonVariants = {
            primary: "btn-primary",
            secondary: "btn-secondary",
        };
        const propertiesToCopy = [
            "background-color",
            "background-image",
            "border",
            "color",
            "font-family",
            "font-weight",
            "text-transform",
        ];
        const styles = {
            primary: "",
            secondary: "",
            custom: "",
        };

        function copyStyle(styleFrom, styleTo) {
            const hasBorder = parseFloat(styleFrom.getPropertyValue("border-width")) > 0;
            for (const style of propertiesToCopy) {
                if (style === "border" && !hasBorder) {
                    // We do not copy the "border" property if border-width is 0
                    // However, we change the border width to ensure visual consistency in preview
                    styles[styleTo] += "border-width: 0px !important;";
                    continue;
                }
                const value = styleFrom.getPropertyValue(style);
                if (value) {
                    styles[styleTo] += `${style}: ${value};`;
                }
            }
        }

        const iframeDocument = el.ownerDocument;
        for (const [variantName, variantClass] of Object.entries(buttonVariants)) {
            const tempButtonEl = iframeDocument.createElement("a");
            tempButtonEl.className = `btn ${variantClass}`;
            this.dependencies.domObserver.ignore(() =>
                el.insertAdjacentElement("afterend", tempButtonEl)
            );
            const computedStyle = getComputedStyle(tempButtonEl);
            copyStyle(computedStyle, variantName);
            this.dependencies.domObserver.ignore(() => tempButtonEl.remove());
        }

        // The style for btn-custom is always a copy of the current button style.
        // This way, if a custom button is currently in use, the customization is
        // correctly represented in the button preview. Otherwise, the custom
        // button style represents the style that the button would adopt once
        // the customization begins. The button is cloned to prevent copying its
        // hovered style.
        const tempButtonEl = el.cloneNode(true);
        this.dependencies.domObserver.ignore(() =>
            el.insertAdjacentElement("afterend", tempButtonEl)
        );
        const computedStyle = getComputedStyle(tempButtonEl);
        copyStyle(computedStyle, "custom");
        this.dependencies.domObserver.ignore(() => tempButtonEl.remove());

        return styles;
    }

    getHasAlpha(styles) {
        // Check for rgba or hsla with alpha < 1
        const hasAlpha = {};
        for (const [variant, styleStr] of Object.entries(styles)) {
            const rgbaMatch = styleStr.match(/background-color: rgba\([^)]+,\s*([0-9.]+)\)/);
            const hslaMatch = styleStr.match(/background-color: hsla\([^)]+,\s*([0-9.]+)\)/);
            const alpha = rgbaMatch
                ? parseFloat(rgbaMatch[1])
                : hslaMatch
                ? parseFloat(hslaMatch[1])
                : 1;
            hasAlpha[variant] = alpha < 1;
        }
        return hasAlpha;
    }

    findColorCombination(el) {
        // Crawl the DOM upwards until a cc class is found, otherwise return cc1
        const ccClasses = ["o_cc1", "o_cc2", "o_cc3", "o_cc4", "o_cc5"];
        const ccSelector = ccClasses.map((cls) => `.${cls}`).join(",");
        const ccElement = el.closest(ccSelector);
        if (!ccElement) {
            return ccClasses[0];
        }
        const matchedClass = ccClasses.find((cls) => ccElement.classList?.contains(cls));
        return matchedClass;
    }
}

export class ButtonStyleAction extends BuilderAction {
    static id = "buttonStyleAction";

    apply({ editingElement, params, value }) {
        const mode = params.mainParam;
        if (mode === "type") {
            this.applyDefaultInlineStyle(editingElement, value);
            if (value !== "custom") {
                editingElement.style.removeProperty("--btn-custom-color");
                editingElement.style.removeProperty("--btn-custom-hover-bg");
            }
        }

        editingElement.className = computeButtonClasses(editingElement, {
            type: mode === "type" ? value : getButtonType(editingElement),
            size: mode === "size" ? value : getButtonSize(editingElement),
            shape: mode === "shape" ? value : getButtonShape(editingElement),
        });
    }

    applyDefaultInlineStyle(el, currentType) {
        const styleProps = ["color", "backgroundColor", "backgroundImage", "border"];
        if (currentType === "custom") {
            withoutTransition(el, () => {
                const computedStyle = el.ownerDocument.defaultView.getComputedStyle(el);
                for (const prop of styleProps) {
                    if (computedStyle[prop] !== "none") {
                        el.style[prop] = computedStyle[prop];
                        if (prop === "color") {
                            el.style.setProperty("--btn-custom-color", computedStyle[prop]);
                        }
                    }
                }
                if (computedStyle.borderStyle === "none") {
                    el.style.borderStyle = "solid";
                }
                updateCustomHoverBackground(el);
            });
        } else {
            for (const prop of styleProps) {
                el.style[prop] = "";
            }
        }
    }

    getValue({ editingElement, params }) {
        const mode = params.mainParam;
        switch (mode) {
            case "type":
                return getButtonType(editingElement);
            case "size":
                return getButtonSize(editingElement);
            case "shape":
                return getButtonShape(editingElement);
        }
    }

    isApplied({ editingElement, params, value }) {
        return this.getValue({ editingElement, params }) === value;
    }
}

export class ButtonFillColorAction extends StyleAction {
    static id = "buttonFillColorAction";
    static dependencies = ["color"];
    apply({ editingElement: el }) {
        withoutTransition(el, () => {
            super.apply(...arguments);
            updateCustomHoverBackground(el);
        });
    }

    getValue(context) {
        // This override is needed because when the button is in outline mode,
        // the color is not shown unless we hover the button
        const { editingElement: el } = context;
        return el.style.backgroundImage || el.style.backgroundColor || super.getValue(context);
    }
}

export class ButtonColorAction extends StyleAction {
    static id = "buttonColorAction";
    apply({ editingElement: el, value }) {
        super.apply(...arguments);
        el.style.setProperty("--btn-custom-color", value);
    }

    getValue(context) {
        // This override is needed because when the button has a custom hover,
        // the color shown in the color picker is otherwise that of the :hover
        // state. The variable is read from the computed style so that theme
        // colors (e.g. "var(--o-color-1)") are resolved.
        const { editingElement: el } = context;
        const color = el.ownerDocument.defaultView
            .getComputedStyle(el)
            .getPropertyValue("--btn-custom-color")
            .trim();
        return color ? normalizeCSSColor(color) : super.getValue(context);
    }
}

registry.category("builder-plugins").add(ButtonStyleOptionPlugin.id, ButtonStyleOptionPlugin);
registry.category("builder-options").add(ButtonStyleOption.id, ButtonStyleOption);
