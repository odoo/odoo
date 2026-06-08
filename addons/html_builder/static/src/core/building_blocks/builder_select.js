import { useRef, useSubEnv } from "@web/owl2/utils";
import { Component, onMounted, props, t, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useVisibilityObserver, useApplyVisibility, useSelectableComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { setElementContent } from "@web/core/utils/html";

export class WithIgnoreItem extends Component {
    static template = xml`<t t-call-slot="default"/>`;
    static props = {
        slots: { type: Object },
    };
    setup() {
        useSubEnv({
            ignoreBuilderItem: true,
        });
    }
}

export class BuilderSelect extends Component {
    static template = "html_builder.BuilderSelect";
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        className: t.string().optional(),
        dropdownContainerClass: t.string().optional(),
        disabled: t.boolean().optional(),
        slots: t.object({
            default: t.object(), // Content is not optional
            fixedButton: t.object().optional(),
        }),
        dropdownClass: t.string().optional("o-hb-select-dropdown"),
    });
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
    };

    setup() {
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.dropdown = useDropdownState();

        const buttonRef = useRef("button");
        let currentLabel;
        const updateCurrentLabel = () => {
            if (!this.props.slots.fixedButton) {
                const newHtml = currentLabel || _t("None");
                if (buttonRef.el && buttonRef.el.innerHTML !== newHtml) {
                    setElementContent(buttonRef.el, newHtml);
                }
            }
        };
        useSelectableComponent(this.props.id, {
            onItemChange(item) {
                currentLabel = item.getLabel();
                updateCurrentLabel();
            },
        });
        onMounted(updateCurrentLabel);
        useSubEnv({
            onSelectItem: () => {
                this.dropdown.close();
            },
        });
    }
}
