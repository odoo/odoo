import { user } from "@web/core/user";

async function isEdispatchDisplayedTR({ config, searchModel }, allowedPickingTypeCodes) {
    if (config.viewType === "form") {
        return false;
    }
    const { resModel, globalContext: { restricted_picking_type_code } = {}, orm } = searchModel;
    if (resModel !== "stock.picking" || !allowedPickingTypeCodes.includes(restricted_picking_type_code)) {
        return false;
    }
    const [company] = await orm.searchRead(
        "res.company",
        [["id", "=", user.activeCompany.id]],
        ["country_code"]
    );
    return company?.country_code === "TR";
}

export const isEdispatchUploadDisplayedTR = (ctx) => isEdispatchDisplayedTR(ctx, ["incoming"]);
export const isEdispatchFetchDisplayedTR = (ctx) => isEdispatchDisplayedTR(ctx, ["incoming", "outgoing"]);
