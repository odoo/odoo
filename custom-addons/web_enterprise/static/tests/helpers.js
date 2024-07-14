/** @odoo-module */

import { createWebClient } from "@web/../tests/webclient/helpers";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

export function createEnterpriseWebClient(params) {
    params.WebClientClass = WebClientEnterprise;
    return createWebClient(params);
}
