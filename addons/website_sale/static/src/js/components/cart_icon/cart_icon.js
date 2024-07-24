/** @odoo-module **/

import { Component, useEffect, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CartIcon {
    setup() {
        this.websiteSaleService = useService("website_sale"); // TODO VCR hook on the service for quick information related to the cart
        this.websiteSaleContext = useState(this.websiteSaleService.context);
        this.websiteSaleTestCart = useRef('website_sale_test_cart');


        useEffect( // TODO VCR add the class to grow the number when it changes
            () => {},
            () => [this.websiteSaleContext.nbItemsInCart]
        )
    }
}

registry.category("public_components").add("website_sale.CartIcon", CartIcon);
