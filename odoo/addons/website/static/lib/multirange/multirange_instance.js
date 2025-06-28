/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import multirange from "@website/../lib/multirange/multirange_custom";

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
