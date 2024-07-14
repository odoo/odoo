/** @odoo-module **/

import { registry } from "@web/core/registry";

export const signInfoService = {
    dependencies: [],
    start() {
        let signInfo = {};

        function set(data) {
            Object.assign(signInfo, data);
        }

        function reset(data) {
            signInfo = data;
        }

        function get(key) {
            return signInfo[key];
        }

        return {
            set,
            reset,
            get,
        };
    },
};

registry.category("services").add("signInfo", signInfoService);
