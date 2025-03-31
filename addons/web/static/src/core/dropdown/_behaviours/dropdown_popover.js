import { Component, onMounted, onRendered, onWillDestroy, onWillStart, xml } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class DropdownPopover extends Component {
    static components = { DropdownItem };
    static template = xml`
        <t t-if="this.props.items">
            <t t-foreach="this.props.items" t-as="item" t-key="this.getKey(item, item_index)">
                <DropdownItem class="item.class" onSelected="() => item.onSelected()" t-out="item.label"/>
            </t>
        </t>
        <t t-slot="content" />
    `;
    static props = {
        // Popover service
        close: { type: Function, optional: true },

        // Events & Handlers
        beforeOpen: { type: Function, optional: true },
        onOpened: { type: Function, optional: true },
        onClosed: { type: Function, optional: true },

        // Rendering & Context
        refresher: Object,
        slots: Object,
        items: { type: Array, optional: true },
    };

    setup() {
        onRendered(() => {
            // Note that the Dropdown component and the DropdownPopover component
            // are not in the same context.
            // So when the Dropdown component is re-rendered, the DropdownPopover
            // component must also re-render itself.
            // This is why we subscribe to this reactive, which is changed when
            // the Dropdown component is re-rendered.
            this.props.refresher.token;
        });

        onWillStart(async () => {
            await this.props.beforeOpen?.();
        });

        onMounted(() => {
            this.props.onOpened?.();
        });

        onWillDestroy(() => {
            this.props.onClosed?.();
        });
    }

    getKey(item, index) {
        return "id" in item ? item.id : index;
    }
}
