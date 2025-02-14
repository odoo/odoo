import { Component, useRef, xml } from "@odoo/owl";
import { useIsChildLarger, useReactivePopover } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

class ListContainerPopover extends Component {
    static props = {
        items: Array,
        slots: { type: Object },
        close: Function,
    };
    static template = xml`
        <div class="d-flex p-2 flex-wrap" style="gap: 0.5rem;">
            <t t-foreach="props.items" t-as="item" t-key="item_index">
                <t t-slot="default" item="item" />
            </t>
        </div>
    `;
}
class ListContainerDialog extends ListContainerPopover {
    static components = { ListContainerPopover, Dialog };
    static template = xml`
        <Dialog title="title" footer="false">
            <ListContainerPopover t-props="props" t-on-click="props.close"/>
        </Dialog>
    `;
    setup() {
        this.title = _t("Choose an order");
    }
}
export class ListContainer extends Component {
    static props = {
        items: Array,
        slots: { type: Object },
    };
    static template = xml`
            <div t-ref="container" class="d-flex overflow-hidden" style="gap: 0.5rem;">
                <t t-if="!ui.isSmall" t-foreach="props.items" t-as="item" t-key="item_index">
                    <t t-slot="default" item="item"/>
                </t>
            </div>
            <button t-if="(isLarger() or ui.isSmall) and props.items.length" t-on-click="toggle"
                class="btn btn-secondary ms-2"
                t-attf-class="fa {{popover.isOpen ? 'fa-caret-up' : 'fa-caret-down'}}"/>
    `;
    setup() {
        this.isLarger = useIsChildLarger("container");
        this.container = useRef("container");
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.popover = useReactivePopover(ListContainerPopover, {
            position: "top-fit",
            arrow: false,
            animation: false,
            closeOnClickAway: (target) => !target.classList.contains("fa-caret-up"),
            onClose: () => {
                this.container.el.style.height = "auto";
            },
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
        // the popover will position itself underneath the specified div,
        // but in this case we want it to be right on top of it;
        // in order to do this we set the height of our div to 0 for the
        // duration that the popover is shown.
        // this.container.el.style.height = 0;
        this.popover.open(this.container.el, {
            items: this.props.items,
            slots: this.props.slots,
        });
    }
}
