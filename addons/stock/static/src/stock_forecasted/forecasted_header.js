import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, markup, useRef } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";

export class LeadDaysPopover extends Component {
    static template = "stock.LeadDaysPopover";
    static props = {leadTime: Object, close: { type: Function, optional: true } };
}

export class ForecastedHeader extends Component {
    static template = "stock.ForecastedHeader";
    static props = { docs: Object, openView: Function };
    static components = { LeadDaysPopover };

    setup(){
        this.orm = useService("orm");
        this.action = useService("action");
        this.popover = usePopover(LeadDaysPopover, { position: "bottom" });
        this.leadTimeRef = useRef("leadTime");
        this._formatFloat = (num) => formatFloat(num, { digits: this.props.docs.precision });
    }

    openPopover() {
        if (!this.popover.isOpen) {
            this.popover.open(this.leadTimeRef.el, {leadTime: this.leadTime });
        }
    }

    async _onClickInventory(){
        const productIds = this.props.docs.product_variants_ids;
        const action = await this.orm.call('product.product', 'action_open_quants', [productIds]);
        if (action.help) {
            action.help = markup(action.help);
        }
        return this.action.doAction(action);
    }

    get products() {
        return this.props.docs.product;
    }

    get leadTime() {
        if (!this.products || this.products.length === 0) {
            return null;
        }
        const productsArray = Object.values(this.products || {});
        const leadTime = structuredClone(productsArray.reduce((minProduct, p) => {
            if (
            !minProduct ||
            (p.leadtime && p.leadtime.total_delay < (minProduct.leadtime?.total_delay ?? Infinity))
            ) {
            return p;
            }
            return minProduct;
        }, null).leadtime);
        const today = new luxon.DateTime.now();
        leadTime["today"] = formatDate(today);
        leadTime["earliestPossibleArrival"] = formatDate(
            today.plus({ days: leadTime.total_delay })
        );
        const details = leadTime.details.filter((d) => d[0] !== "Time Horizon");
        const formattedDetails = [];
        let intermediaryDate = today;
        for (const [title, delay] of details.reverse()) {
            if (typeof delay == 'string') {
                formattedDetails.push([title, delay, false]);
            } else {
                intermediaryDate = intermediaryDate.plus({ days: delay });
                formattedDetails.push([title, formatDate(intermediaryDate), true]);
            }
        }
        leadTime.details = formattedDetails;
        return leadTime;
    }

    get leadTimeShort() {
        let short = " " + (this.leadTime.total_delay) + " day(s)";
        if (this.leadTime.total_delay != 0) {
            short += " (" + this.leadTime.earliestPossibleArrival + ")";
        }
        return short;
    }

    get quantityOnHand() {
        return Object.values(this.products).reduce((sum, product) => sum + product.quantity_on_hand, 0);
    }

    get incomingQty() {
        return Object.values(this.products).reduce((sum, product) => sum + product.incoming_qty, 0);
    }

    get outgoingQty() {
        return Object.values(this.products).reduce((sum, product) => sum + product.outgoing_qty, 0);
    }

    get virtualAvailable() {
        return Object.values(this.products).reduce((sum, product) => sum + product.virtual_available, 0);
    }

    get uom() {
        return Object.values(this.products)[0].uom;
    }

    toJsonString(obj) {
        return JSON.stringify(obj);
    }
}
