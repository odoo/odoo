import { BusParametersPlugin } from "@bus/bus_parameters_plugin";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(BusParametersPlugin, {
    setup() {
        super.setup();
        this.serverURL = session.livechatData.serverUrl.replace(/\/+$/, "");
    },
});
