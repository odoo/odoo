import { user } from "@web/core/user";
import { useEnv } from "@web/owl2/utils";

async function isEdispatchDisplayedTR(allowedPickingTypeCodes) {
    const env = useEnv();
    if (env.config.viewType === "form") {
        return false;
    }
    const { resModel, globalContext: { restricted_picking_type_code } = {}, orm } = env.searchModel;
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

export const isEdispatchUploadDisplayedTR = () => isEdispatchDisplayedTR(["incoming"]);
export const isEdispatchFetchDisplayedTR = () => isEdispatchDisplayedTR(["incoming", "outgoing"]);
