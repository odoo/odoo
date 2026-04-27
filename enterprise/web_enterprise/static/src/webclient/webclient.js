/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { useService } from "@web/core/utils/hooks";
import { EnterpriseNavBar } from "./navbar/navbar";

export class WebClientEnterprise extends WebClient {
    static components = {
        ...WebClient.components,
        NavBar: EnterpriseNavBar,
    };
    setup() {
        super.setup();
        this.hm = useService("home_menu");
    }
    _loadDefaultApp() {
        return this.hm.toggle(true);
    }
}
