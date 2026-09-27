import { Component, onMounted, onWillDestroy, onWillStart, t, useProps, xml } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class DropdownPopover extends Component {
    static components = { DropdownItem };
    static template = xml`
        <t t-if="this.props.items">
            <t t-foreach="this.props.items" t-as="item" t-key="this.getKey(item, item_index)">
                <DropdownItem class="item.class" onSelected="() => item.onSelected()" t-out="item.label"/>
            </t>
        </t>
        <t t-call-slot="content" />
    `;

    props = useProps({
        // Popover service
        close: t.function().optional(),
        // Events & Handlers
        beforeOpen: t.function([], t.promise()).optional(),
        onOpened: t.function([]).optional(),
        onClosed: t.function([]).optional(),
        // Rendering & Context
        items: t
            .array(
                t.object({
                    label: t.string(),
                    onSelected: t.function(),
                    class: t.any().optional(),
                })
            )
            .optional(),
        slots: t.object({
            default: t.any().optional(),
            content: t.any().optional(),
        }),
    });

    setup() {
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
