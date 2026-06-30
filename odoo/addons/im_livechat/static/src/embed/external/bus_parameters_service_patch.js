/* @odoo-module */

import { busParametersService } from "@bus/bus_parameters_service";

import { serverUrl } from "@im_livechat/embed/common/livechat_data";

import { patch } from "@web/core/utils/patch";

patch(busParametersService, {
    start() {
        return {
            ...super.start(...arguments),
            serverURL: serverUrl.replace(/\/+$/, ""),
        };
    },
});
