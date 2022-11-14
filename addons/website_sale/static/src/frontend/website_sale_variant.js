/** @odoo-module **/

import VariantMixin from "sale.VariantMixin";

export const WebsiteSaleVariantMixin = {
    ...VariantMixin,
    isWebsite: true,
};
