import { OutOfFocusService, outOfFocusService } from "@mail/core/common/out_of_focus_service";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

export const UNREAD_MSG_TITLE = 100;

patch(OutOfFocusService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.titleService = services.title;
        this.counter = 0;
        env.bus.addEventListener("window_focus", () => this.clearUnreadMessage());
        this.intervalShowing = true;
    },
    clearUnreadMessage() {
        this.counter = 0;
        this.titleService.setParts({ [UNREAD_MSG_TITLE]: undefined });
        this.intervalShowing = true;
        this.titlePattern = undefined;
        clearInterval(this.newMessageInterval);
    },
    setInterval(func, duration) {
        return setInterval(func, duration);
    },
    updateTitle() {
        this.titleService.setParts({
            [UNREAD_MSG_TITLE]: this.intervalShowing
                ? sprintf(this.titlePattern, this.counter)
                : undefined,
        });
    },
    notify() {
        super.notify(...arguments);
        clearInterval(this.newMessageInterval);
        this.counter++;
        this.titlePattern = this.counter === 1 ? _t("%s Message") : _t("%s Messages");
        this.updateTitle();
        this.newMessageInterval = this.setInterval(() => {
            this.updateTitle();
            this.intervalShowing = !this.intervalShowing;
        }, 1_000);
    },
});
outOfFocusService.dependencies = [...outOfFocusService.dependencies, "title"];
