import { OutOfFocusService } from "./out_of_focus_service";
import { usePlugin } from "@odoo/owl";
import { TitlePlugin } from "@web/core/browser/title_plugin";
import { patch } from "@web/core/utils/patch";

patch(OutOfFocusService.prototype, {
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
