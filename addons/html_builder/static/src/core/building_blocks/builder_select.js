import { Component, onMounted, signal, t, useProps, xml } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { setElementContent } from "@web/core/utils/html";
import { useSubEnv } from "@web/owl2/utils";
import {
    basicContainerBuilderComponentProps,
    useApplyVisibility,
    useSelectableComponent,
    useVisibilityObserver,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class WithIgnoreItem extends Component {
    static template = xml`<t t-call-slot="default"/>`;

    props = useProps({
        slots: t.object(),
    });

    setup() {
        useSubEnv({
            ignoreBuilderItem: true,
        });
    }
}

export const builderSelectProps = {
    ...basicContainerBuilderComponentProps,
    className: t.string().optional(),
    dropdownContainerClass: t.string().optional(),
    disabled: t.boolean().optional(),
    slots: t.object({
        default: t.object(), // Content is not optional
        fixedButton: t.object().optional(),
    }),
    dropdownClass: t.string().optional("o-hb-select-dropdown"),
};

export class BuilderSelect extends Component {
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
    };
    static template = "html_builder.BuilderSelect";

    props = useProps(builderSelectProps);
    buttonRef = signal.ref();
    rootRef = signal.ref();
    contentRef = signal.ref();

    setup() {
        useVisibilityObserver(this.contentRef, useApplyVisibility(this.rootRef));

        this.dropdown = useDropdownState();

        this.currentLabel = null;
        useSelectableComponent(this.props, {
            onItemChange: (item) => {
                this.currentLabel = item.getLabel();
                this.updateCurrentLabel();
            },
        });
        onMounted(() => this.updateCurrentLabel());
        useSubEnv({
            onSelectItem: () => {
                this.dropdown.close();
            },
        });
    }

    updateCurrentLabel() {
        if (!this.props.slots.fixedButton) {
            const newHtml = this.currentLabel || _t("None");
            const buttonEl = this.buttonRef();
            if (buttonEl && buttonEl.innerHTML !== newHtml) {
                setElementContent(buttonEl, newHtml);
            }
        }
    }
}
