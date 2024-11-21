import { Component, EventBus, onMounted, useRef, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { basicContainerWeWidgetProps, useWeComponent } from "../builder_helpers";
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
    };
    setup() {
        const button = useRef("button");
        useWeComponent();
        this.dropdown = useDropdownState();
        this.firstRender = true;
        onMounted(() => (this.firstRender = false));
        useSubEnv({
            weSelectBus: new EventBus(),
            weSetSelectLabel: (labelHtml) => {
                button.el.innerHTML = labelHtml;
            },
        });
        useBus(this.env.weSelectBus, "select-item", (item) => {
            this.dropdown.close();
        });
    }
}
