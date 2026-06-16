import { formatDate } from "@web/core/l10n/dates";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, markup, signal, t, useProps, usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { usePopover } from "@web/core/popover/popover_hook";

export class LeadDaysPopover extends Component {
    static template = "stock.LeadDaysPopover";
    props = useProps({
        leadTime: t.object(),
        close: t.function().optional(),
    });
}

export class ForecastedHeader extends Component {
    static template = "stock.ForecastedHeader";
    props = useProps({
        docs: t.object(),
        openView: t.function(),
    });
    static components = { LeadDaysPopover };

    setup() {
        this.orm = usePlugin(ORM);
        this.action = usePlugin(ActionPlugin);
        this.popover = usePopover(LeadDaysPopover, { position: "bottom" });
        this.leadTimeRef = signal.ref();
        this._formatFloat = (num) => formatFloat(num, { digits: [0, this.props.docs.precision] });
    }

    openPopover() {
        if (!this.popover.isOpen) {
            this.popover.open(this.leadTimeRef(), { leadTime: this.leadTime });
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
        const today = luxon.DateTime.now();
        leadTime.today = formatDate(today);
        leadTime.earliestPossibleArrival = formatDate(today.plus({ days: leadTime.total_delay }));
        const formattedDetails = [];
        let intermediaryDate = today;
        for (const [title, delay] of leadTime.details.reverse()) {
            if (delay === "total_delay_title") {
                formattedDetails.push([
                    title,
                    "= " + leadTime.earliestPossibleArrival,
                    "table-info",
                ]);
            } else if (typeof delay === "string") {
                formattedDetails.push([title, delay, ""]);
            } else {
                intermediaryDate = intermediaryDate.plus({ days: delay });
                formattedDetails.push([title, formatDate(intermediaryDate), "table-secondary"]);
            }
        }
        leadTime.details = formattedDetails;
        return leadTime;
    }

    get leadTimeShort() {
        let short = " " + (this.leadTime.total_delay) + " days";
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
}
