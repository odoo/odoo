import { useLayoutEffect } from "@web/owl2/utils";
import { Component, props, signal, t } from "@odoo/owl";
import { CenteredIcon } from "@point_of_sale/app/components/centered_icon/centered_icon";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { formatCurrency } from "@web/core/currency";
import { BadgeTag } from "@web/core/tags_list/badge_tag";

// This methods is service-less, see PoS knowledges for more information
export const orderDisplayProps = {
    order: t.object(),
    slots: t.object(),
    mode: t.string().optional("display"), // display, receipt
};

export class OrderDisplay extends Component {
    static template = "point_of_sale.OrderDisplay";
    static components = { CenteredIcon, Orderline, BadgeTag };
    props = props(orderDisplayProps);

    setup() {
        this.scrollableRef = signal.ref();
        useLayoutEffect(() => {
            this.scrollableRef()
                ?.querySelector(".orderline.selected")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.order.currency.id);
    }

    get comboSortedLines() {
        return this.order.getOrderlines().reduce((acc, line) => {
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
