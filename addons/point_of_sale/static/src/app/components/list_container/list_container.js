import { Component, useEffect, useRef, xml } from "@odoo/owl";
import { useIsChildLarger } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

class ListContainerDialog extends Component {
    static components = { Dialog };
    static props = {
        items: Array,
        slots: { type: Object },
        close: Function,
    };
    static template = xml`
        <Dialog title="title" footer="false">
            <div class="list-container-items d-flex p-2 flex-wrap" style="gap: 0.5rem;">
                <t t-foreach="props.items" t-as="item" t-key="item_index">
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
        <div class="d-flex gap-1 align-items-center flex-grow-1" t-attf-class="{{props.class}}" t-att-class="{'overflow-hidden': !isUiSmall}">
            <button t-if="props.onClickPlus" class="list-plus-btn btn btn-secondary btn-lg flex-shrink-0 lh-lg" t-on-click="props.onClickPlus">
                <i class="fa fa-fw fa-plus-circle" aria-hidden="true"/>
            </button>
            <span t-if="props.onClickPlus" class="navbar-separator mx-1"/>
            <div class="overflow-hidden flex-grow-1">
                <div t-ref="container" class="list-container-items d-flex align-items-center gap-1">
                    <div t-if="!props.forceSmall" t-foreach="props.items" t-as="item" t-key="item_index" t-att-class="{'invisible order-2': shouldBeInvisible(item_index)}">
                        <t t-slot="default" item="item"/>
                    </div>
                    <button t-if="this.sizing.isLarger or props.forceSmall" t-on-click="toggle"
                        class="btn btn-lg btn-secondary order-1 flex-shrink-0 fw-bolder lh-lg"
                        t-att-class="props.forceSmall ? '' : 'px-3 fw-bold'">
                        <i t-if="props.forceSmall" class="fa fa-fw fa-caret-down"/>
                        <t t-else="">+<t t-esc="hiddenCount"/></t>
                    </button>
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
    get hiddenCount() {
        return this.props.items.length - this.sizing.maxItems;
    }
    toggle() {
        this.dialog.add(ListContainerDialog, {
            items: this.props.items,
            slots: this.props.slots,
        });
    }
}
