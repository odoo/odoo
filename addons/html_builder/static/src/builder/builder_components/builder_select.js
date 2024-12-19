import { Component, EventBus, onMounted, useRef, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    useBuilderComponent,
    BuilderComponent,
} from "./utils";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useBus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class BuilderSelect extends Component {
    static template = "html_builder.BuilderSelect";
    static props = {
        ...basicContainerBuilderComponentProps,
        slots: Object,
    };
    static components = {
        Dropdown,
        BuilderComponent,
    };

    setup() {
        this.buttonRef = useRef("button");
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));
        this.dropdown = useDropdownState();
        this.selectableItems = [];
        this.setItem = this.setItem.bind(this);
        const setLabelDebounced = useDebounced(this.setItem, 0);

        useSubEnv({
            actionBus: new EventBus(),
            BuilderSelectContext: {
                bus: new EventBus(),
                addSelectableItem: (item) => {
                    this.selectableItems.push(item);
                },
                removeSelectableItem: (item) => {
                    const index = this.selectableItems.indexOf(item);
                    if (index !== -1) {
                        this.selectableItems.splice(index, 1);
                    }
                },
                update: setLabelDebounced,
                getSelectedItemId: () => this.currentSelectedItemId,
            },
        });

        onMounted(this.setItem);
        useBus(this.env.editorBus, "STEP_ADDED", (ev) => {
            if (ev.detail.isPreviewing) {
                return;
            }
            this.setItem();
        });
        useBus(this.env.BuilderSelectContext.bus, "select-item", (item) => {
            this.dropdown.close();
        });
    }
    setItem() {
        let currentItem;
        let itemPriority = 0;
        for (const selectableItem of this.selectableItems) {
            if (selectableItem.isActive() && selectableItem.priority >= itemPriority) {
                currentItem = selectableItem;
                itemPriority = selectableItem.priority;
            }
        }
        if (currentItem) {
            this.buttonRef.el.innerHTML = currentItem.getLabel();
        }
        if (currentItem && currentItem.id !== this.currentSelectedItemId) {
            this.currentSelectedItemId = currentItem.id;
            this.env.dependencyManager.triggerDependencyUpdated();
        }
    }
}
