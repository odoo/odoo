odoo.define('website_sale.tour_mock_tracking', function (require) {

const publicWidget = require('web.public.widget');
const websiteSaleTracking = require('website_sale.tracking');

require('website_sale.website_sale');

const events = {
    view_item: [],
    add_to_cart: [],
    remove_from_cart: [],
};

let promise;

publicWidget.registry.WebsiteSale.include({
    _getCombinationInfo() {
        promise = this._super(...arguments);
        return promise;
    },
});

publicWidget.registry.WebsiteSale.getCombinationInfoPromise = function () {
    let result = promise;
    promise = undefined;
    return result;
};

websiteSaleTracking.include({
    _onViewItem(event, data) {
        events.view_item.push(data);
    },
    _onAddToCart(event, data) {
        events.add_to_cart.push(data);
    },
});

websiteSaleTracking.getEvents = function (eventName) {
    return events[eventName];
};

});
