import { BusParametersPlugin } from "@bus/bus_parameters_plugin";
import { session } from "@web/session";
import { plugin, Plugin } from "@odoo/owl";
import { services } from "@web/core/services";

export class LivechatBusParametersPlugin extends Plugin {
    setup() {
        const busParameters = plugin(BusParametersPlugin);
        const serverURL = session.livechatData.serverUrl.replace(/\/+$/, "");
        busParameters.serverURL.set(serverURL);
    }
}

services.add(LivechatBusParametersPlugin);
