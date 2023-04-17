/** @odoo-module **/

import { Component, onMounted, onWillDestroy, xml } from "@odoo/owl";
import { nextId } from "@web/core/popover/popover";
import { DropdownItem } from "../dropdown_item";

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
        close: Function,

        // Events & Handlers
        onOpened: { type: Function, optional: true },
        onClosed: { type: Function, optional: true },

        // Rendering & Context
        renderRef: Object,
        env: Object,
        slots: Object,
        items: { type: Array, optional: true },
    };

    setup() {
        this.id = nextId();
        this.__owl__.childEnv = this.props.env;
        this.props.renderRef.render = () => this.render();

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
