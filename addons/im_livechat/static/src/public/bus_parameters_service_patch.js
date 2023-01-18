/** @odoo-module */

import { busParametersService } from "@bus/bus_parameters_service";

import { serverUrl } from "@im_livechat/livechat_data";

import { patch } from "@web/core/utils/patch";

patch(busParametersService, "im_livechat", {
    start() {
        return {
            ...this._super(...arguments),
            serverURL: serverUrl.replace(/\/+$/, ""),
        };
    },
});
