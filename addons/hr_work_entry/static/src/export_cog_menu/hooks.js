import { user } from "@web/core/user";

export async function baseExportCogDisplayCondition({ config, searchModel, isSmall }) {
    const baseOk = (
        !isSmall &&
        searchModel.resModel === "hr.employee" &&
        config.actionType === "ir.actions.act_window" &&
        ["gantt", "calendar", "list", "pivot", "form"].includes(config.viewType)
    );
    if (!baseOk) {
        return false;
    }

    const userCompany = await searchModel.orm.read(
        "res.company",
        [user.activeCompany.id],
        ["country_code"]
    );
    return userCompany[0]?.country_code === "BE";
}

export async function isBelgianCompanyActive(orm) {
    const currentCompanyId = user.activeCompany.id;
    const data = await orm.searchRead("res.company", [["id", "=", currentCompanyId]], ["country_code"])
    const countryCode = data[0].country_code;
    return countryCode === "BE";
}
