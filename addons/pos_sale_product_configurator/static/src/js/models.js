/** @odoo-module */

import { Gui } from "@point_of_sale/js/Gui";
import { Order } from "@point_of_sale/js/models";
import Registries from "@point_of_sale/js/Registries";
import { ConnectionLostError, ConnectionAbortedError } from "@web/core/network/rpc_service";
import { identifyError } from "@point_of_sale/js/utils";

const PosSaleProductConfiguratorOrder = (Order) =>
    class PosSaleProductConfiguratorOrder extends Order {
        async add_product(product, options) {
            super.add_product(...arguments);
            if (product.optional_product_ids.length) {
                // The `optional_product_ids` only contains ids of the product templates and not the product itself
                // We don't load all the product template in the pos, so it'll be hard to know if the id comes from
                // a product available in POS. We send a quick cal to the back end to verify.
                const isProductLoaded = await this.pos.env.services.rpc({
                    model: "product.product",
                    method: "has_optional_product_in_pos",
                    args: [[product.id]],
                });
                if (isProductLoaded) {
                    try {
                        const quantity = this.get_selected_orderline().get_quantity();
                        const info = await this.pos.getProductInfo(product, quantity);
                        Gui.showPopup("ProductInfoPopup", { info: info, product: product });
                    } catch (e) {
                        if (
                            identifyError(e) instanceof ConnectionLostError ||
                            ConnectionAbortedError
                        ) {
                            Gui.showPopup("OfflineErrorPopup", {
                                title: this.env._t("Network Error"),
                                body: this.env._t(
                                    "Cannot access product information screen if offline."
                                ),
                            });
                        } else {
                            Gui.showPopup("ErrorPopup", {
                                title: this.env._t("Unknown error"),
                                body: this.env._t(
                                    "An unknown error prevents us from loading product information."
                                ),
                            });
                        }
                    }
                }
            }
        }
    };
Registries.Model.extend(Order, PosSaleProductConfiguratorOrder);
