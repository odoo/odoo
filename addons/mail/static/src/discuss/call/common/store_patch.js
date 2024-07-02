import { Record } from "@mail/model/record";
import { Store } from "@mail/model/store";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
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
