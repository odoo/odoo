import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { user } from "@web/core/user";

export class AttendanceOvertimeListModel extends RelationalModel {
    async _loadData(config, cache) {
        config.domain = await this._getActiveCompaniesRulesetDomain();
        return super._loadData(config, cache);
    }

    async _getActiveCompaniesRulesetDomain() {
        const company_ids = user.activeCompanies.map((company) => company.id);
        const company_countries = await this.orm.searchRead(
            "res.company",
            [["id", "in", company_ids]],
            ["country_id"]
        );
        const country_ids = company_countries.map((country) => country.country_id[0]);
        return ["|", ["country_id", "=", false], ["country_id", "in", country_ids]];
    }
}

registry.category("views").add("hr_attendance_overime_ruleset_list", {
    ...listView,
    Model: AttendanceOvertimeListModel,
});
