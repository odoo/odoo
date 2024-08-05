import { Component, useRef, xml } from "@odoo/owl";
import { useIsChildLarger, useReactivePopover } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

class ListContainerPopover extends Component {
    static props = {
        items: Array,
        slots: { type: Object },
        close: Function,
    };
    static template = xml`
        <div class="d-flex p-2 flex-wrap" style="gap: 0.5rem;">
            <t t-foreach="props.items" t-as="item" t-key="item_index">
                <t t-slot="default" item="item" t-on-click="props.close"/>
            </t>
        </div>
    `;
}
class ListContainerDialog extends ListContainerPopover {
    static components = { ListContainerPopover, Dialog };
    static template = "point_of_sale.ListContainerDialog";
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
        <div class="overflow-hidden d-flex" t-attf-class="{{props.class}}">
            <!-- it's important that the parent of the 'container' div not be the parent of the 'view more' div -->
            <!-- otherwise the appearance and disappearance of the 'view more' div will retrigger the resizeObserver, -->
            <!-- which will cause a glitch-->
            <div class="overflow-hidden">
                <!-- the popover will position itself underneath the specified div, -->
                <!-- but in this case we want it to be right on top of it; -->
                <!-- in order to do this we set the height of our div to 0 for the -->
                <!-- duration that the popover is shown. -->
                <div t-ref="container" class="d-flex" t-attf-style="
                    gap: 0.5rem;
                    height: {{popover.isOpen ? '0' : 'auto'}};
                ">
                    <t t-if="!props.forceSmall" t-foreach="props.items" t-as="item" t-key="item_index">
                        <t t-slot="default" item="item"/>
                    </t>
                </div>
            </div>
            <button t-if="props.onClickPlus" class="btn btn-light btn-lg" t-on-click="props.onClickPlus">
                <i class="fa fa-fw fa-lg fa-plus-circle" aria-hidden="true"/>
            </button>
            <button t-if="isLarger() or props.forceSmall" t-on-click="toggle"
                class="btn btn-secondary ms-2"
                t-attf-class="fa {{popover.isOpen ? 'fa-caret-up' : 'fa-caret-down'}}"/>
        </div>
    `;
    setup() {
        this.container = useRef("container");
        this.isLarger = useIsChildLarger(this.container);
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.popover = useReactivePopover(ListContainerPopover, {
            position: "bottom-fit",
            arrow: false,
            animation: false,
            popoverClass: "mh-50 overflow-y-auto overflow-x-hidden",
            closeOnClickAway: (target) => !target.classList.contains("fa-caret-up"),
        });
    }
    toggle() {
        if (this.ui.isSmall) {
            this.dialog.add(ListContainerDialog, {
                items: this.props.items,
                slots: this.props.slots,
            });
            return;
        }
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        this.popover.open(this.container.el, {
            items: this.props.items,
            slots: this.props.slots,
        });
    }
}
