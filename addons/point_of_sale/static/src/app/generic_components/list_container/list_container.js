import { Component, useEffect, useRef, xml } from "@odoo/owl";
import { useIsChildLarger } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

class ListContainerDialog extends Component {
    static components = { Dialog };
    static props = {
        items: Array,
        slots: { type: Object },
        close: Function,
    };
    static template = xml`
        <Dialog title.translate="Choose an order" footer="false">
            <div class="d-flex p-2 flex-wrap" style="gap: 0.5rem;">
                <t t-foreach="props.items" t-as="item" t-key="item_index">
                    <t t-slot="default" item="item" />
                </t>
            </div>
        </Dialog>
    `;
}

export class ListContainer extends Component {
    static props = {
        items: Array,
        onClickPlus: { type: Function, optional: true },
        slots: { type: Object },
        class: { type: String, optional: true },
        forceSmall: { type: Boolean, optional: true },
    };
    static defaultProps = {
        class: "",
    };
    static template = xml`
        <div class="overflow-hidden d-flex flex-grow-1" t-attf-class="{{props.class}}">
            <button t-if="props.onClickPlus" class="list-plus-btn btn btn-secondary btn-lg me-1" t-on-click="props.onClickPlus">
                <i class="fa fa-fw fa-plus-circle" aria-hidden="true"/>
            </button>
            <button t-if="this.sizing.isLarger or props.forceSmall" t-on-click="toggle"
                class="btn btn-secondary mx-1 fa fa-caret-down" />
            <div class="overflow-hidden w-100 position-relative">
                <div t-ref="container" class="d-flex w-100">
                    <div t-if="!props.forceSmall" t-foreach="props.items" t-as="item" t-key="item_index" t-att-class="{'invisible': shouldBeInvisible(item_index)}">
                        <t t-slot="default" item="item"/>
                    </div>
                </div>
            </div>
        </div>
    `;
    setup() {
        this.container = useRef("container");
        this.sizing = useIsChildLarger(this.container);
        this.ui = useService("ui");
        this.dialog = useService("dialog");

        useEffect(
            () => {
                this.sizing.reload();
            },
            () => [this.props.items]
        );
    }
    shouldBeInvisible(itemIndex) {
        return itemIndex >= this.sizing.maxItems;
    }
    toggle() {
        this.dialog.add(ListContainerDialog, {
            items: this.props.items,
            slots: this.props.slots,
        });
    }
}
