/** @odoo-module */

import { user } from "@web/core/user";

export async function isReceiptTR({ config, searchModel }) {
    if (config.viewType === "form") {
        return false;
    }
    const { resModel, globalContext: { restricted_picking_type_code } = {}, orm } = searchModel;
    if (resModel !== "stock.picking" || restricted_picking_type_code !== "incoming") {
        return false;
    }
    const [company] = await orm.searchRead(
        "res.company",
        [["id", "=", user.activeCompany.id]],
        ["country_code"]
    );
    return company?.country_code === "TR";
}

export async function isReceiptOrDeliveryTR({ config, searchModel }) {
    if (config.viewType === "form") {
        return false;
    }
    const { resModel, globalContext: { restricted_picking_type_code } = {}, orm } = searchModel;
    if (
        resModel !== "stock.picking" ||
        !["incoming", "outgoing"].includes(restricted_picking_type_code)
    ) {
        return false;
    }
    const [company] = await orm.searchRead(
        "res.company",
        [["id", "=", user.activeCompany.id]],
        ["country_code"]
    );
    return company?.country_code === "TR";
}
