/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// TODO: remove in master
publicWidget.registry.BlogPostLink = publicWidget.registry.postLink.extend({
    selector: "select[name='archive'], span:has(.fa-calendar-o) a",
});
