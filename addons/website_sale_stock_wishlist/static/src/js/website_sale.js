/** @odoo-module **/

import publicWidget from "web.public.widget";
import "website_sale.website_sale";
import ajax from "web.ajax";
import { qweb as QWeb } from "web.core";

const loadXml = async () => {
  return ajax.loadXML(
    "/website_sale_stock_wishlist/static/src/xml/product_availability.xml",
    QWeb
  );
};

publicWidget.registry.WebsiteSale.include({
  /**
   * It will display additional info messages regarding the select product's stock and the wishlist.
   * @override
   */
  _onChangeCombination: function (ev, $parent, combination) {
    this._super.apply(this, arguments);
    loadXml().then(function () {
      if ($('.o_add_wishlist_dyn').length) {
        var $message = $(
          QWeb.render(
            "website_sale_stock_wishlist.product_availability",
            combination
          )
        );
        $message.appendTo($("div.availability_messages"));
      }
    });
  },
});

