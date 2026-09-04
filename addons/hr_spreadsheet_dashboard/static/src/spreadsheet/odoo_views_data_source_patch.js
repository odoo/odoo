import { patch } from "@web/core/utils/patch";
import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { user } from "@web/core/user";

patch(OdooViewsDataSource.prototype, {
    getComputedDomain() {
        const domainList = super.getComputedDomain();
        if (this._metaData?.resModel === "hr.employee") {
            for (const leaf of domainList) {
                if (Array.isArray(leaf) && leaf[0] === "company_id" && leaf[1] === "in") {
                    leaf[2] = user.context.allowed_company_ids;
                }
            }
        }
        return domainList;
    },
});
