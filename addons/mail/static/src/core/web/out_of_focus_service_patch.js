/* @odoo-module */

import { OutOfFocusService, outOfFocusService } from "@mail/core/common/out_of_focus_service";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

patch(OutOfFocusService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.titleService = services.title;
        this.counter = 0;
        env.bus.addEventListener("window_focus", () => {
            this.counter = 0;
            this.titleService.setParts({ _chat: undefined });
        });
    },
    notify() {
        super.notify(...arguments);
        this.counter++;
        const titlePattern = this.counter === 1 ? _t("%s Message") : _t("%s Messages");
        this.titleService.setParts({ _chat: sprintf(titlePattern, this.counter) });
    },
});
outOfFocusService.dependencies = [...outOfFocusService.dependencies, "title"];
