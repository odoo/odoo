import { BusParametersPlugin } from "@bus/bus_parameters_plugin";
import { session } from "@web/session";
import { Plugin, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";

export class LivechatBusParametersPlugin extends Plugin {
    setup() {
        const busParameters = usePlugin(BusParametersPlugin);
        const serverURL = session.livechatData.serverUrl.replace(/\/+$/, "");
        busParameters.serverURL = serverURL;
    }
}

services.add(LivechatBusParametersPlugin);
