import { Record } from "@mail/core/common/record";
import { DiscussApp } from "@mail/core/common/discuss_app_model";
import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup() {
        super.setup(...arguments);
        // mailboxes in sidebar
        this.inbox = Record.one("Thread");
        this.starred = Record.one("Thread");
        this.history = Record.one("Thread");
    },
});
