import { Component, EventBus, onMounted, useEnv, useRef, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    BuilderComponent,
    useSelectableComponent,
} from "./utils";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useBus } from "@web/core/utils/hooks";

export class BuilderSelect extends Component {
    static template = "html_builder.BuilderSelect";
    static props = {
        ...basicContainerBuilderComponentProps,
        id: { type: String, optional: true },
        slots: Object,
    };
    static components = {
        Dropdown,
        BuilderComponent,
    };

    setup() {
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.dropdown = useDropdownState();

        const buttonRef = useRef("button");
        let currentLabel;
        const updateCurrentLabel = () => {
            if (buttonRef.el) {
                buttonRef.el.innerHTML = currentLabel;
            }
        };
        const selectableContext = useSelectableComponent(this.props.id, {
            onItemChange(item) {
                currentLabel = item.getLabel();
                updateCurrentLabel();
            },
        });
        onMounted(updateCurrentLabel);
        useSubEnv({ selectableContext });
        useBus(selectableContext.selectableBus, "SELECT_ITEM", (item) => {
            this.dropdown.close();
        });
    }
}
