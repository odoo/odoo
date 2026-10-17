import { Plugin, signal, usePlugin, useScope } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";
import { user } from "@web/core/user";
import { ReminderPopover } from "@hr/components/reminder_popover";

export class ReminderPlugin extends Plugin {
    popover = usePlugin(PopoverPlugin);
    scope = useScope();

    schedule(isEligible, getMessage, onAction) {
        const target = signal.ref();
        const key = `hr.reminder.${user.userId}`;
        const today = () => luxon.DateTime.now().toISODate();
        let close;
        const timeout = browser.setTimeout(() => {
            if (isEligible() && browser.localStorage.getItem(key) !== today()) {
                close = this.popover.add(target(), ReminderPopover, {
                    message: getMessage(),
                    onAction: () => {
                        close();
                        onAction();
                    },
                }, {
                    closeOnClickAway: false,
                    closeOnEscape: false,
                    popoverClass: "o_hr_reminder_popover",
                    onClose: () => browser.localStorage.setItem(key, today()),
                });
            }
        }, 2 * 60 * 1000);
        this.scope.onDestroy(() => {
            browser.clearTimeout(timeout);
            close?.();
        });
        return target;
    }
}
