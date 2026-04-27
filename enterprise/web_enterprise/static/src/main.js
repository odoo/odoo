/** @odoo-module **/

import { startWebClient } from "@web/start";
import { WebClientEnterprise } from "./webclient/webclient";

/**
 * This file starts the enterprise webclient. In the manifest, it replaces
 * the community main.js to load a different webclient class
 * (WebClientEnterprise instead of WebClient)
 */
startWebClient(WebClientEnterprise);
