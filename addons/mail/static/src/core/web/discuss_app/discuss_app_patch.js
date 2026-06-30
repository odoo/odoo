import { useLayoutEffect } from "@web/owl2/utils";

import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

import { patch } from "@web/core/utils/patch";
import { ControlPanel } from "@web/search/control_panel/control_panel";

Object.assign(Discuss.components, { ControlPanel });

patch(Discuss.prototype, {
    setup() {
        super.setup();
        useLayoutEffect(
            (threadName) => {
                if (threadName) {
                    this.env.config?.setDisplayName(threadName);
                }
            },
            () => [this.thread?.displayName]
        );
    },
});
