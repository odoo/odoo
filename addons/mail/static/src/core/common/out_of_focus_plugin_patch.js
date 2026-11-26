import { OutOfFocusPlugin } from "@mail/core/common/out_of_focus_plugin";
import { usePlugin } from "@odoo/owl";
import { TitlePlugin } from "@web/core/browser/title_plugin";
import { patch } from "@web/core/utils/patch";

patch(OutOfFocusPlugin.prototype, {
    setup() {
        super.setup(...arguments);
        this.title = usePlugin(TitlePlugin);
        this.counter = 0;
    },

    clearUnreadMessage() {
        super.clearUnreadMessage();
        this.counter = 0;
        this.title.prefix.set("");
    },
    async notify() {
        await super.notify(...arguments);
        this.counter++;
        this.title.prefix.set(`(${this.counter})`);
    },
});
