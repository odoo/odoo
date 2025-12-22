import { Component, useEffect, useRef } from "@odoo/owl";
import { CenteredIcon } from "@point_of_sale/app/generic_components/centered_icon/centered_icon";
import { _t } from "@web/core/l10n/translation";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { formatMonetary } from "@web/views/fields/formatters";

export class OrderWidget extends Component {
    static template = "point_of_sale.OrderWidget";
    static props = {
        lines: { type: Array, element: Object, optional: true },
        slots: { type: Object, optional: true },
        taxTotals: { type: Object, optional: true },
        style: { type: String, optional: true },
        class: { type: String, optional: true },
        generalNote: { type: String, optional: true },
        screenName: { type: String, optional: true },
    };
    static defaultProps = {
        style: "",
        class: "",
    };
    static components = { CenteredIcon, Orderline };

    setup() {
        this.scrollableRef = useRef("scrollable");
        this.formatMonetary = formatMonetary;
        useEffect(() => {
            this.scrollableRef.el
                ?.querySelector(".orderline.selected")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }

    emptyCartText() {
        return _t("Start adding products");
    }
}
