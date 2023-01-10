/** @odoo-module **/

import * as publicWidget from 'web.public.widget'

publicWidget.registry.ProductCategoriesLinks = publicWidget.Widget.extend({
    selector: '.products_categories',
    events: {
        'click [data-link-href]': '_openLink',
    },

    _openLink: function (ev) {
        window.location.href = ev.currentTarget.getAttribute('data-link-href');
    },
});
