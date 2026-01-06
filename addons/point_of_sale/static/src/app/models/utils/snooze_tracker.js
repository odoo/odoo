const { DateTime } = luxon;
import { reactive } from "@odoo/owl";

const REFRESH_DELAY = 1000;

export class SnoozedProductTracker {
    constructor(snoozes) {
        this.state = reactive({ activeSnoozes: new Set(), snoozedProductIds: new Set() });
        if (snoozes) {
            this.setSnoozes(snoozes);
        }
    }

    setSnoozes(snoozes) {
        this.snoozes = (snoozes || []).filter(Boolean);
        this.refresh();
    }

    getSnoozes() {
        return this.snoozes;
    }

    refresh() {
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
            this.updateTimeout = null;
        }

        if (!this.snoozes || this.snoozes.length === 0) {
            this.state.activeSnoozes = [];
            this.state.snoozedProductIds = new Set();
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

    getActiveSnooze(product) {
        if (!this.isProductSnoozed(product)) {
            return null;
        }
        for (const snooze of this.state.activeSnoozes) {
            if (snooze.product_template_id?.id === product.id) {
                return snooze;
            }
        }
        return null;
    }

    isProductSnoozed(product) {
        return this.state.snoozedProductIds.has(product.id); // ensure reactivity is triggered when snoozedProductIds is updated
    }
}
