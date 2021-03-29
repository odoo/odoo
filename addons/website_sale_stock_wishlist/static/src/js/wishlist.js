/** @odoo-module **/

import publicWidget from "web.public.widget";
import "website_sale_wishlist.wishlist";

publicWidget.registry.ProductWishlist.include({
  events: _.extend(
    {},
    publicWidget.registry.ProductWishlist.prototype.events,
    {
      "click .wishlist-section .o_notify_stock": "_onClickNotifyStock",
    }
  ),
  /**
   * It will remove wishlist indication when adding a product to the wishlist.
   * @override
   */
  _addNewProducts: function () {
    this._super.apply(this, arguments);
    this.$("#stock_wishlist_message").addClass("d-none");
  },
  /**
   * @private
   * @param {Event} ev
   */
  _onClickNotifyStock: function (ev) {
    const tr = $(ev.currentTarget).parents("tr");
    const wish = tr.data("wish-id");
    const icon = $(ev.currentTarget).find("i");
    const currentNotify = ev.currentTarget.dataset.notify === 'True';
    this._rpc({
      route: "/shop/wishlist/notify/" + wish,
      params: {
        notify: !currentNotify,
      }
    }).then((notify) => {
      ev.currentTarget.dataset.notify = notify ? 'True' : 'False';
      icon.toggleClass("fa-check-square-o", notify);
      icon.toggleClass("fa-square-o", !notify);
    });
  },
});

