import { Component, onMounted, useRef, useSubEnv, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    useSelectableComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { setElementContent } from "@web/core/utils/html";

export class WithIgnoreItem extends Component {
    static template = xml`<t t-slot="default"/>`;
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
    static props = {
        ...basicContainerBuilderComponentProps,
        className: { type: String, optional: true },
        dropdownContainerClass: { type: String, optional: true },
        slots: {
            type: Object,
            shape: {
                default: Object, // Content is not optional
                fixedButton: { type: Object, optional: true },
            },
        },
    };
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
    };

    setup() {
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.dropdown = useDropdownState();

        this.buttonRef = useRef("button");
        let currentLabel;
        const updateCurrentLabel = () => {
            if (!this.props.slots.fixedButton) {
                const newHtml = currentLabel || _t("None");
                if (this.buttonRef.el && this.buttonRef.el.innerHTML !== newHtml) {
                    setElementContent(this.buttonRef.el, newHtml);
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

    heightOfButton() {
        return this.buttonRef.el.getBoundingClientRect().height;
    }
}
