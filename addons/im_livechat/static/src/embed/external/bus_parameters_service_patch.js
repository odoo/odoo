import { busParametersService } from "@bus/bus_parameters_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { isEmbedLivechatEnabled } from "../common/misc";

patch(busParametersService, {
    start(env) {
        if (!isEmbedLivechatEnabled(env)) {
            return super.start(...arguments);
        }
        return {
            ...super.start(...arguments),
            serverURL: session.livechatData.serverUrl?.replace(/\/+$/, ""),
        };
    },
});
