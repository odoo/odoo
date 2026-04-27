/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { mocks } from "@web/../tests/helpers/mock_services";

patch(mocks, {
    iot_websocket: () => ({}),
});
