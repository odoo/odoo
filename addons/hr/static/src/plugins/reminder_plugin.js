import { onWillDestroy, Plugin, signal, useListener, usePlugin } from "@odoo/owl";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";
import { user } from "@web/core/user";
import { ReminderPopover } from "@hr/components/reminder_popover";

const today = () => luxon.DateTime.now().toISODate();

export class ReminderPlugin extends Plugin {
    popover = usePlugin(PopoverPlugin);
    target = signal.ref();
    key = `hr.reminder.${user.userId}`;

    setup() {
        useListener(window, "storage", ({ key, newValue }) => {
            if (key === this.key) {
                if (newValue) {
                    this.close?.();
                } else if (!this.close) {
                    this.start();
                }
            }
        });
        onWillDestroy(() => {
            clearTimeout(this.timeout);
            this.close?.();
        });
    }

    schedule(isEligible, message, dropdown) {
        Object.assign(this, { isEligible, message, dropdown });
        this.start();
        return this.target;
    }

    dismiss() {
        localStorage.setItem(this.key, today());
    }

    reset() {
        localStorage.removeItem(this.key);
        this.start();
    }

    start() {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
            if (
                this.isEligible() &&
                !this.dropdown.isOpen &&
                localStorage.getItem(this.key) !== today()
            ) {
                this.close = this.popover.add(this.target(), ReminderPopover, {
                    message: this.message,
                    onAction: () => this.dropdown.open(),
                }, {
                    closeOnClickAway: false,
                    closeOnEscape: false,
                    setActiveElement: false,
                    popoverClass: "o_hr_reminder_popover",
                    onClose: () => {
                        this.close = null;
                        this.dismiss();
                    },
                });
            }
        }, 2 * 60 * 1000);
    }
}
