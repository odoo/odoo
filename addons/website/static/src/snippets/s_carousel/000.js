/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.Carousel = publicWidget.Widget.extend({
    selector: ".s_carousel_wrapper",

    /**
     * @override
     */
    willStart() {
        // TODO: remove in master
        this.el.querySelector(".carousel").setAttribute("data-bs-ride", "carousel");
        return this._super(...arguments);
    },
});

export default publicWidget.registry.Carousel;
