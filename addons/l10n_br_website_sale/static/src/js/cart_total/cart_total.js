import { useState } from '@odoo/owl';
import { CartTotal } from '@website_sale/js/cart_total/cart_total';
import { patch } from '@web/core/utils/patch';


patch(CartTotal.prototype, {
    setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            country_code: '',
        })
    },
});
