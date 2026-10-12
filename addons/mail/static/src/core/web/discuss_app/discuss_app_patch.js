import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

import { useOnChange } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";
import { ControlPanel } from "@web/search/control_panel/control_panel";

Object.assign(Discuss.components, { ControlPanel });

patch(Discuss.prototype, {
    setup() {
        super.setup();
        useOnChange(
            () => [this.thread?.displayName],
            (threadName) => {
                if (threadName) {
                    this.env.config?.setDisplayName(threadName);
                }
            }
        );
    },
});
