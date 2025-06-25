import { OutOfFocusService, outOfFocusService } from "@mail/core/common/out_of_focus_service";
import { patch } from "@web/core/utils/patch";

patch(OutOfFocusService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.titleService = services.title;
        this.counter = 0;
        this.contributingMessageLocalIds = new Set();
        env.bus.addEventListener("window_focus", () => this.clearUnreadMessage());
    },
    clearUnreadMessage() {
        this.counter = 0;
        this.contributingMessageLocalIds.clear();
        this.titleService.setCounters({ discuss: undefined });
    },
    notify(message) {
        if (this.contributingMessageLocalIds.has(message.localId)) {
            return;
        }
        this.contributingMessageLocalIds.add(message.localId);
        this.counter++;
        this.titleService.setCounters({ discuss: this.counter });
        super.notify(...arguments);
    },
});
outOfFocusService.dependencies = [...outOfFocusService.dependencies, "title"];
