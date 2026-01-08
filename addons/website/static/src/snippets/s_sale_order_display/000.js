/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { renderToElement } from "@web/core/utils/render";


publicWidget.registry.sale_order_display = publicWidget.Widget.extend({
    selector: '.s_sale_order_display',
    disabledInEditableMode: false,

    events: {
        'click .load-more-btn': '_onLoadMore',
    },

    start: function () {
        this.offset = 0;
        this._renderOrders({ reset: true });
        return this._super(...arguments);
    },

    _renderOrders: async function ({ reset = false } = {}) {
        const showConfirm = this.el.dataset.showConfirm === 'true';
        const view = this.el.dataset.view || 'list';
        const limit = parseInt(this.el.dataset.limit || 3);

        if (reset) {
            this.offset = 0;
        }

        const orders = await jsonrpc("/sale_order_display/data", {
            offset: this.offset,
            limit: limit,
            confirmed_only: showConfirm,
        });

        this.orders = reset ? orders : [...(this.orders || []), ...orders];

        const tmpl = view === 'list'
            ? 'website.s_sale_order_display_list'
            : 'website.s_sale_order_display_card';

        const newDomElement = renderToElement(tmpl, { sale_orders: this.orders });
        this.el.querySelector('.container').replaceChildren(newDomElement);

        this.offset += orders.length;

        if (orders.length >= limit) {
            const loadMoreBtn = document.createElement('div');
            loadMoreBtn.className = 'text-center mt-3';
            loadMoreBtn.innerHTML = `<button type="button" class="btn btn-primary load-more-btn">Load More</button>`;
            this.el.querySelector('.container').appendChild(loadMoreBtn);
        }
    },

    _onLoadMore: function () {
        this._renderOrders();
    },
});
