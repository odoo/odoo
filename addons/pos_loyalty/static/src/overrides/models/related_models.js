/* @odoo-module */

import { CONFIG } from "@point_of_sale/app/models/related_models";

CONFIG.exemptedAutomaticLoad.push(
    (field) => field.model === "loyalty.reward" && field.name === "all_discount_product_ids",
    (field) => field.model === "loyalty.rule" && field.name === "valid_product_ids"
);
