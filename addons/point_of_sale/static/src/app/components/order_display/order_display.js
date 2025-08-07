import { Component, useEffect, useRef } from "@odoo/owl";
import { CenteredIcon } from "@point_of_sale/app/components/centered_icon/centered_icon";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { TagsList } from "@web/core/tags_list/tags_list";

// This methods is service-less, see PoS knowledges for more information
export class OrderDisplay extends Component {
    static template = "point_of_sale.OrderDisplay";
    static components = { CenteredIcon, Orderline, TagsList };
    static props = {
        order: Object,
        slots: Object,
        mode: { type: String, optional: true }, // display, receipt
    };
    static defaultProps = {
        mode: "display",
    };

    setup() {
        this.scrollableRef = useRef("scrollable");
        useEffect(() => {
            this.scrollableRef.el
                ?.querySelector(".orderline.selected")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.order.currency.id);
    }

    emptyCartText() {
        return _t("Start adding products");
    }

    get comboSortedLines() {
        return this.order.lines.reduce((acc, line) => {
            if (line.combo_line_ids?.length > 0) {
                acc.push(line, ...line.combo_line_ids);
            } else if (!line.combo_parent_id) {
                acc.push(line);
            }
            return acc;
        }, []);
    }

    get order() {
        return this.props.order;
    }

    getInternalNotes() {
        return JSON.parse(this.props.order.internal_note || "[]");
    }
}
