/* @odoo-module */

import { DiscussApp } from "@mail/core/common/discuss_app_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp, {
    new(data) {
        const app = super.new(data);
        Record.onChange(app, "ringingThreads", () => {
            if (app.ringingThreads.length > 0) {
                this.env.services["mail.sound_effects"].play("incoming-call", { loop: true });
            } else {
                this.env.services["mail.sound_effects"].stop("incoming-call");
            }
        });
        return app;
    },
});

patch(DiscussApp.prototype, {
    setup() {
        super.setup();
        this.ringingThreads = Record.many("Thread");
    },
});
