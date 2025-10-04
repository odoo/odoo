/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { Call } from "@mail/discuss/call/common/call";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call });

patch(Discuss.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useState(useService("discuss.rtc"));
    },
});
