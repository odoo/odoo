import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";

export const companyAutocompleteService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        if (session.iap_company_enrich) {
            orm.silent.call("res.company", "iap_enrich_auto", [user.activeCompany.id], {});
        }
    },
};

registry
    .category("services")
    .add("partner_autocomplete.companyAutocomplete", companyAutocompleteService);
