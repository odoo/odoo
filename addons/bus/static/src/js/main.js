/** @odoo-module **/
import { busCrosstabCommunication } from "@bus/services/crosstab_communication";
import { busLocalstorageCommunication } from "@bus/services/localstorage_communication";
import { longpollingCommunicationService } from "@bus/services/longpolling_communication";
import { busServerCommunication } from "@bus/services/server_communication";

import env from "web.commonEnv";

// deployment order is important
const services = [
    busLocalstorageCommunication,
    busCrosstabCommunication,
    longpollingCommunicationService,
    busServerCommunication,
];

for (const { deploy, name } of services) {
    env.services[name] = deploy(env);
}
