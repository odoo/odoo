/** @odoo-module */

import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";

export class StockMove extends Component {
    static props = {
        clickable: Boolean,
        displayUOM: Boolean,
        label: { optional: true, type: String },
        parent: Object,
        record: Object,
        uom: { optional: true, type: Object },
    };
    static template = "mrp_workorder.StockMove";

    setup() {
        this.fieldState = "state";
        this.isLongPressable = false;
        this.longPressed = false;
        this.resModel = this.props.record.resModel;
        this.resId = this.props.record.resId;
    }

    get cssClass() {
        let cssClass = this.isLongPressable ? "o_longpressable" : "";
        if (this.isComplete) {
            cssClass += " text-muted";
        }
        return cssClass;
    }

    get isComplete() {
        return Boolean(this.props.record.data.picked);
    }

    get toConsumeQuantity() {
        const move = this.props.record.data;
        const parent = this.props.parent.data;
        let toConsumeQuantity = move.should_consume_qty || move.product_uom_qty;
        if (parent.product_tracking == "serial") {
            toConsumeQuantity /= this.props.parent.data.product_qty;
        }
        return toConsumeQuantity;
    }

    get quantityDone() {
        return this.props.record.data.quantity;
    }

    get uom() {
        if (this.props.displayUOM) {
            return this.props.record.data.product_uom[1];
        }
        return this.toConsumeQuantity === 1 ? _t("Unit") : _t("Units");
    }

    longPress() {}

    onAnimationEnd(ev) {
        if (ev.animationName === "longpress") {
            this.longPressed = true;
            this.longPress();
        }
    }

    onClick() {
        if (!this.props.clickable) {
            return;
        }
        if (this.longPressed) {
            this.longPressed = false;
            return; // Do nothing since the longpress event was already called.
        }
        this.clicked();
    }

    async clicked() {
        const action = await this.props.record.model.orm.call(
            this.resModel,
            "action_show_details",
            [this.resId]
        );
        const options = {
            onClose: async () => {
                this.props.record.load();
            },
        };
        this.props.record.model.action.doAction(action, options);
    }

    async toggleQuantityDone() {
        if (!this.props.clickable) {
            return;
        } else if (!this.toConsumeQuantity) {
            return this.clicked();
        }
        const quantity = this.quantityDone ? this.quantityDone : this.toConsumeQuantity;
        this.props.record.update({
            quantity: quantity,
            picked: !this.isComplete,
        });
        this.props.record.save({ reload: false });
    }

    get state() {
        return this.props.record.data[this.fieldState];
    }
}
