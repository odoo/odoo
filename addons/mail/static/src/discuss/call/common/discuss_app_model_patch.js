import { DiscussApp } from "@mail/core/common/discuss_app_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup() {
        super.setup();
        this.ringingThreads = Record.many("Thread", {
            /** @this {import("models").DiscussApp} */
            onUpdate() {
                if (this.ringingThreads.length > 0) {
                    this.store.env.services["mail.sound_effects"].play("incoming-call", {
                        loop: true,
                    });
                } else {
                    this.store.env.services["mail.sound_effects"].stop("incoming-call");
                }
            },
        });
    },
});
