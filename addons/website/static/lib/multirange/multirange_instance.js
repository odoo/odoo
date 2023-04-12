/** @odoo-module alias=website_sale.multirange.instance **/

import publicWidget from "web.public.widget";
import multirange from "website_sale.multirange";

publicWidget.registry.WebsiteMultirangeInputs = publicWidget.Widget.extend({
    selector: 'input[type=range][multiple]:not(.multirange)',

    /**
     * @override
     */
    start() {
        return this._super.apply(this, arguments).then(() => {
            multirange.init(this.el);
        });
    },
});
