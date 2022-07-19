/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import { parseDate, formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

import { formatFloat } from "@web/views/fields/formatters";

const { Component, onWillUpdateProps } = owl;

class PaymentPopOver extends Component {}
PaymentPopOver.template = "AccountPaymentPopOver";

export class AccountPaymentField extends Component {
    setup() {
        this.popover = usePopover();
        this.orm = useService("orm");
        this.action = useService("action");

        this.formatData(this.props);
        onWillUpdateProps((nextProps) => this.formatData(nextProps));
    }

    formatData(props) {
        let info = JSON.parse(props.value) || {
            content: [],
            outstanding: false,
            title: "",
            move_id: this.props.record.data.id
        };
        for (let [k, v] of Object.entries(info.content)) {
            v.index = k;
            v.amount = formatFloat(v.amount, {digits: v.digits});
            if (v.date) v.date = formatDate(parseDate(v.date));
        }
        this.lines = info.content;
        this.outstanding = info.outstanding;
        this.title = info.title;
        this.move_id = info.move_id;
    }

    onInfoClick(ev, idx) {
        const isClosed = !document.querySelector(".o_payment_popover");
        if (isClosed) {
            this.currentPopoverEl = null;
        }
        if (this.popoverCloseFn) {
            this.closePopover();
        }
        if (isClosed || this.currentPopoverEl !== ev.currentTarget) {
            this.currentPopoverEl = ev.currentTarget;
            this.popoverCloseFn = this.popover.add(
                ev.currentTarget,
                this.constructor.components.Popover,
                {
                    title: this.env._t("Journal Entry Info"),
                    ...this.lines[idx],
                    _onRemoveMoveReconcile: this.removeMoveReconcile.bind(this),
                    _onOpenPaymentOrMove: this.openPaymentOrMove.bind(this),
                },
                {
                    position: localization.direction === "rtl" ? "bottom" : "left",
                },
            );
        }
    }

    closePopover() {
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }

    async outstandingCreditAssign(id) {
        await this.orm.call(this.props.record.resModel, 'js_assign_outstanding_line', [this.move_id, id], {});
        await this.props.record.model.root.load();
        this.props.record.model.notify();
    }

    async removeMoveReconcile(move_id, partial_id) {
        this.closePopover();
        await this.orm.call(this.props.record.resModel, 'js_remove_outstanding_partial', [move_id, partial_id], {});
        await this.props.record.model.root.load();
        this.props.record.model.notify();
    }

    async openPaymentOrMove(model, id) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: id,
            views: [[false, 'form']],
            target: 'current'
        });
    }
}
AccountPaymentField.template = "AccountPaymentInfo";
AccountPaymentField.supportedTypes = ["char"];
AccountPaymentField.components = {
    Popover: PaymentPopOver,
}

registry.category("fields").add("payment", AccountPaymentField);
