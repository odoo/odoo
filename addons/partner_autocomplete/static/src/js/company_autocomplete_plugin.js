import { Plugin, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { ORM } from "@web/core/orm_plugin";
import { session } from "@web/session";
import { user } from "@web/core/user";

export class CompanyAutocompletePlugin extends Plugin {
    #orm = usePlugin(ORM);

    setup() {
        if (session.iap_company_enrich) {
            this.#orm.silent.call("res.company", "iap_enrich_auto", [user.activeCompany.id], {});
        }
    }
}

services.add(CompanyAutocompletePlugin);
