import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon;

const REFRESH_DELAY = 1000;

export class SnoozeTracker {
    constructor(snoozes) {
        this.state = proxy({ activeSnoozes: new Array(), snoozedProductIds: new Set(), now: 0 });
        if (snoozes) {
            this.setSnoozes(snoozes);
        }
    }

    setSnoozes(snoozes) {
        this.snoozes = (snoozes || []).filter(Boolean);
        this.refresh();
    }

    refresh() {
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
            this.updateTimeout = null;
        }

        if (!this.snoozes || this.snoozes.length === 0) {
            this.state.activeSnoozes = [];
            this.state.snoozedProductIds = new Set();
            this.stopCountdown();
            return;
        }

        const now = DateTime.now();
        this.state.activeSnoozes = this.snoozes.filter(
            ({ start_time, end_time }) => start_time <= now && (!end_time || end_time >= now)
        );
        const snoozedProductIds = new Set();
        this.state.activeSnoozes.forEach((snooze) => {
            snoozedProductIds.add(snooze.raw.product_template_id);
        });
        this.state.snoozedProductIds = snoozedProductIds;

        if (this.state.activeSnoozes.some((s) => s.end_time)) {
            this.startCountdown();
        } else {
            this.stopCountdown();
        }

        // Schedule next refresh at earliest relevant boundary:
        // - earliest end among active snoozes
        // - earliest start among future snoozes (so they can become active)
        let earliestUpdate = Infinity;
        const nowMs = now.toMillis();
        for (const s of this.state.activeSnoozes) {
            const endMs = s.end_time?.toMillis();
            if (endMs && endMs < earliestUpdate) {
                earliestUpdate = endMs;
            }
        }
        for (const s of this.snoozes) {
            const startMs = s.start_time.toMillis();
            if (startMs > nowMs && startMs < earliestUpdate) {
                earliestUpdate = startMs;
            }
        }

        if (earliestUpdate === Infinity) {
            return;
        }

        const delay = Math.max(0, earliestUpdate - nowMs);
        this.updateTimeout = setTimeout(() => this.refresh(), delay + REFRESH_DELAY);
    }

    startCountdown() {
        if (this.countdownInterval) {
            return;
        }
        this.state.now = Date.now();
        this.countdownInterval = setInterval(() => {
            this.state.now = Date.now();
        }, REFRESH_DELAY);
    }

    stopCountdown() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
        this.state.now = 0;
    }

    getProductSnoozeLabel(product) {
        const snooze = this.getActiveSnooze("product", { product });
        if (!snooze) {
            return "";
        }

        if (!snooze.end_time) {
            return _t("Snoozed - session");
        }

        const [countdown] = this.getSnoozeCountdown(snooze);
        return countdown ? _t("Snoozed - %s left", countdown) : "";
    }

    getSnoozeCountdown(activeSnooze) {
        if (!activeSnooze) {
            return ["", undefined];
        }

        if (!activeSnooze.end_time) {
            return [_t("Next session"), activeSnooze];
        }

        // Use the shared reactive clock for countdown calculations.
        const now = DateTime.fromMillis(this.state.now || Date.now());
        const diff = activeSnooze.end_time.diff(now, ["hours", "minutes", "seconds"]);

        if (diff.as("seconds") <= 0) {
            return ["", undefined];
        }

        return [diff.toFormat("hh:mm:ss"), activeSnooze];
    }

    getActiveSnooze(type, data = {}) {
        // If a product is found, its snooze record returned; otherwise, the self-order snooze record returned.
        if (type === "product" && data.product) {
            if (!this.isProductSnoozed(data.product)) {
                return null;
            }
            const templateId = data.product.product_tmpl_id?.id ?? data.product.id;
            for (const snooze of this.state.activeSnoozes) {
                if (snooze.product_template_id?.id === templateId) {
                    return snooze;
                }
            }
        }
        return null;
    }

    isProductSnoozed(product) {
        if (!product) {
            return false;
        }
        const templateId = product.product_tmpl_id?.id ?? product.id;
        return this.state.snoozedProductIds.has(templateId);
    }
}
