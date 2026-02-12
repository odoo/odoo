import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
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

class ButtonStyleOptionPlugin extends Plugin {
    static id = "buttonStyleOption";
    resources = {
        builder_options: [ButtonStyleOption],
        builder_actions: { ButtonStyleAction, ButtonFillColorAction },
    };
}

export class ButtonStyleOption extends BaseOptionComponent {
    static template = "html_builder.ButtonStyleOption";
    static selector = ".btn";
    static dependencies = [];
    static components = {
        BuilderColorPicker,
        BuilderSelect,
        BuilderSelectItem,
        BuilderNumberInput,
        BorderConfigurator,
    };

    buttonSizesData = BUTTON_SIZES;
    buttonShapesData = BUTTON_SHAPES;
    buttonTypesData = BUTTON_TYPES;

    setup() {
        super.setup();

        const editingElement = this.env.getEditingElement();
        const computedStyle =
            editingElement.ownerDocument.defaultView.getComputedStyle(editingElement);
        this.state = useDomState((el) => ({
            type: getButtonType(el),
            textColor: computedStyle.color,
            fillColor: computedStyle.backgroundColor,
            border: computedStyle.border,
        }));
    }
}

class ButtonStyleAction extends BuilderAction {
    static id = "buttonStyleAction";
    static dependencies = [];

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

class ButtonFillColorAction extends StyleAction {
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
