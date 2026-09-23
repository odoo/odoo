/** @odoo-module native */
import { Component, useEffect, useRef, xml } from "@odoo/owl";
import { useIsChildLarger } from "@point_of_sale/app/hooks/hooks";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog";
const log = makeLogger("pos.component.list_container");
class ListContainerDialog extends Component {
    static components = { Dialog };
    static props = {
        items: Array,
        slots: { type: Object },
        close: Function,
    };
    static template = xml`
        <Dialog title="this.title" footer="false">
            <div class="list-container-items d-flex p-2 flex-wrap" style="gap: 0.5rem;">
                <t t-foreach="this.props.items" t-as="item" t-key="item_index">
                    <t t-slot="default" item="item" />
                </t>
            </div>
        </Dialog>
    `;
    setup() {
        this.title = _t("Choose an order");
    }
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
        <div class="d-flex flex-grow-1" t-attf-class="{{this.props.class}}" t-att-class="{'overflow-hidden': !this.isUiSmall}">
            <button t-if="this.props.onClickPlus" class="list-plus-btn btn btn-secondary btn-lg me-1 my-2" t-on-click="this.props.onClickPlus">
                <i class="fa-solid fa-plus-circle" aria-hidden="true"/>
            </button>
            <button t-if="this.sizing.isLarger or this.props.forceSmall" t-on-click="this.toggle"
                class="btn btn-secondary mx-1 fa-solid fa-caret-down my-2" />
            <div class="overflow-hidden w-100 position-relative py-2">
                <div t-ref="container" class="list-container-items d-flex w-100">
                    <div t-if="!this.props.forceSmall" t-foreach="this.props.items" t-as="item" t-key="item_index" t-att-class="{'invisible': this.shouldBeInvisible(item_index)}">
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
                log.logic("items changed: resized", () => ({
                    items: this.props.items.length,
                    maxItems: this.sizing.maxItems,
                    isLarger: this.sizing.isLarger,
                }));
            },
            () => [this.props.items],
        );
    }
    shouldBeInvisible(itemIndex) {
        return itemIndex >= this.sizing.maxItems;
    }
    toggle() {
        log.logic("toggle: overflow dialog", () => ({
            items: this.props.items.length,
        }));
        this.dialog.add(ListContainerDialog, {
            items: this.props.items,
            slots: this.props.slots,
        });
    }
}
