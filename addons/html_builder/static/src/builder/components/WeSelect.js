import { Component, EventBus, onMounted, useRef, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import {
    basicContainerWeWidgetProps,
    useVisibilityObserver,
    useApplyVisibility,
    useWeComponent,
    WeComponent,
} from "../builder_helpers";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useBus } from "@web/core/utils/hooks";

export class WeSelect extends Component {
    static template = "html_builder.WeSelect";
    static props = {
        ...basicContainerWeWidgetProps,
        slots: Object,
    };
    static components = {
        Dropdown,
        WeComponent,
    };

    setup() {
        const button = useRef("button");
        useWeComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));
        this.dropdown = useDropdownState();
        const selectableItems = [];
        useSubEnv({
            actionBus: new EventBus(),
            weSelectContext: {
                bus: new EventBus(),
                addSelectableItem: (item) => {
                    selectableItems.push(item);
                },
                removeSelectableItem: (item) => {
                    const index = selectableItems.indexOf(item);
                    if (index !== -1) {
                        selectableItems.splice(index, 1);
                    }
                },
            },
        });
        function setLabel() {
            let item;
            let itemPriority = 0;
            for (const selectableItem of selectableItems) {
                if (selectableItem.isActive() && selectableItem.priority >= itemPriority) {
                    item = selectableItem;
                    itemPriority = selectableItem.priority;
                }
            }
            if (item) {
                button.el.innerHTML = item.getLabel();
            }
        }
        onMounted(setLabel);
        useBus(this.env.editorBus, "STEP_ADDED", (ev) => {
            if (ev.detail.isPreviewing) {
                return;
            }
            setLabel();
        });
        useBus(this.env.weSelectContext.bus, "select-item", (item) => {
            this.dropdown.close();
        });
    }
}
