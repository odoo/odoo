import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { AccordionItem } from "@point_of_sale/app/components/accordion_item/accordion_item";

export class ProductInfoBanner extends Component {
    static template = "point_of_sale.ProductInfoBanner";
    static components = {
        AccordionItem,
    };
    static props = {
        productTemplate: Object,
        product: { type: Object | null, optional: true },
        info: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.state = useState({
            other_warehouses: [],
            available_quantity: 0,
            free_qty: 0,
            uom: "",
        });
    }
}
