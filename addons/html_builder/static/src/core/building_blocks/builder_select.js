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

/**
 * Extends `BuilderSelect` behaviour for components that need to override it.
 *
 * @param {Object} props
 * @returns {Object}
 */
export function useBuilderSelect(props) {
    const rootRef = signal.ref();
    const buttonRef = signal.ref();
    const contentRef = signal.ref();
    let currentLabel = _t("None");

    const dropdown = useDropdownState();

    const updateCurrentLabel = () => {
        if (!props.slots.fixedButton) {
            const newHtml = currentLabel;
            const buttonEl = buttonRef();
            if (buttonEl && buttonEl.innerHTML !== newHtml) {
                setElementContent(buttonEl, newHtml);
            }
        }
    };
    useSelectableComponent(props, {
        onItemChange(item) {
            currentLabel = item.getLabel();
            updateCurrentLabel();
        },
    });
    onMounted(updateCurrentLabel);
    useSubEnv({
        onSelectItem: () => {
            dropdown.close();
        },
    });

    return {
        builderSelectLabel: () => currentLabel,
        buttonRef,
        contentRef,
        dropdown,
        rootRef,
    };
}

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

export const builderSelectComponents = {
    Dropdown,
    BuilderComponent,
    WithIgnoreItem,
};

export class BuilderSelect extends Component {
    static components = builderSelectComponents;
    static template = "html_builder.BuilderSelect";

    props = useProps(builderSelectProps);

    setup() {
        const { builderSelectLabel, buttonRef, contentRef, dropdown, rootRef } = useBuilderSelect(
            this.props
        );
        Object.assign(this, { builderSelectLabel, buttonRef, contentRef, dropdown, rootRef });
        useVisibilityObserver(this.contentRef, useApplyVisibility(this.rootRef));
    }
}
