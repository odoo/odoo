import { busParametersService } from "@bus/bus_parameters_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(busParametersService, {
    start() {
        return {
            ...super.start(...arguments),
            serverURL: session.livechatData.serverUrl.replace(/\/+$/, ""),
        };
    },
});
