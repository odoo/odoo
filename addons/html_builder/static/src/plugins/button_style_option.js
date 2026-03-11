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

export class ButtonStyleOptionPlugin extends Plugin {
    static id = "buttonStyleOption";
    resources = {
        builder_actions: { ButtonStyleAction, ButtonFillColorAction },
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
    static dependencies = ["history"];

    buttonSizesData = BUTTON_SIZES;
    buttonShapesData = BUTTON_SHAPES;
    buttonTypesData = BUTTON_TYPES;

    setup() {
        super.setup();
        this.state = useDomState(async (el) => {
            const buttonType = getButtonType(el);
            const buttonStyles = await this.getButtonStyles(el);
            const state = {
                buttonStyles: buttonStyles,
                buttonCombinationClass: this.findColorCombination(el),
                currentButtonType: buttonType,
                currentButtonTypeData: this.buttonTypesData.find((btn) => btn.type == buttonType),
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
        const previewVariables = [
            "background-color",
            "border",
            "border-radius",
            "color",
            "font-family",
            "font-weight",
            "text-transform",
        ];

        const buttonContainerEl = el.parentElement;
        const iframeDocument = el.ownerDocument;
        const styles = {
            primary: "",
            secondary: "",
            custom: "",
        };
        for (const [variantName, variantClass] of Object.entries(buttonVariants)) {
            const tempButtonEl = iframeDocument.createElement("a");
            tempButtonEl.className = `btn ${variantClass}`;
            this.dependencies.history.ignoreDOMMutations(() =>
                buttonContainerEl.appendChild(tempButtonEl)
            );
            const computedStyle = getComputedStyle(tempButtonEl);
            for (const style of previewVariables) {
                const value = computedStyle.getPropertyValue(style);
                if (value) {
                    styles[variantName] += `${style}: ${value};`;
                }
            }
            this.dependencies.history.ignoreDOMMutations(() => tempButtonEl.remove());
        }

        // The style for btn-custom is always a copy of the current button style.
        // This way, if a custom button is currently in use, the customization is
        // correctly represented in the button preview. Otherwise, the custom
        // button style represents the style that the button would adopt once
        // the customization begins.

        // requestAnimationFrame is a temporary workaround necessary because
        // the change of color seems to be animated even if it should not (see
        // `withoutTransition` in `StyleAction.apply`). This should be removed
        // once the transition problem is fixed.
        await new Promise((resolve) => {
            requestAnimationFrame(() => {
                const computedStyle = getComputedStyle(el);
                for (const style of previewVariables) {
                    const value = computedStyle.getPropertyValue(style);
                    if (value) {
                        styles.custom += `${style}: ${value};`;
                    }
                }
                resolve();
            });
        });
        return styles;
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
                    }
                }
                if (computedStyle.borderStyle === "none") {
                    el.style.borderStyle = "solid";
                }
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

    getValue(context) {
        // This override is needed because when the button is in outline mode,
        // the color is not shown unless we hover the button
        const { editingElement: el } = context;
        return el.style.backgroundColor || el.style.backgroundImage || super.getValue(context);
    }
}

registry.category("builder-plugins").add(ButtonStyleOptionPlugin.id, ButtonStyleOptionPlugin);
registry.category("builder-options").add(ButtonStyleOption.id, ButtonStyleOption);
