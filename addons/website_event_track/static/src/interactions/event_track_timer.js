import { formatDuration } from "@web/core/l10n/dates";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon;

/*
 * Simple implementation of a timer interaction that uses a "time to live" configuration
 * value to countdown seconds on a target element.
 * Will be used to visually countdown the time before a talk starts.
 * When the timer reaches 0, the element destroys itself.
 */
export class WebsiteEventTrackTimer extends Interaction {
    static selector = ".o_we_track_timer";

    dynamicContent = {
        ".close": { "t-on-click": this.onCloseClick },
    };

    setup() {
        const timeToLive = parseInt(this.el.dataset.timeToLive);
        const deadline = DateTime.now().plus({ seconds: timeToLive });
        const remainingMs = deadline.diff(DateTime.now()).as("milliseconds");
        if (remainingMs > 0) {
            this.updateTimerDisplay(remainingMs);
            this.el.classList.remove("d-none");
            this.deadline = deadline;
            this.timer = setInterval(this.refreshTimer.bind(this), 1000);
        } else {
            this.destroy();
        }
    }

    destroy() {
        this.el.parentNode.remove();
        clearInterval(this.timer);
    }

    onCloseClick() {
        this.destroy();
    }

    /**
     * The function will trigger an update if the timer has not yet expired.
     * Otherwise, the component will be destroyed.
     */
    refreshTimer() {
        const remainingMs = this.deadline.diffNow().as("milliseconds");
        if (remainingMs > 0) {
            this.updateTimerDisplay(remainingMs);
        } else {
            this.destroy();
        }
    }

    /**
     * The function will have the responsibility to update the text indicating
     * the time remaining before the counter expires. The function will use
     * Luxon to transform the remaining time in more a human friendly format
     * Example: "in 32 minutes", "in 17 hours", etc.
     * @param {integer} remainingMs - Time remaining before the counter expires (in ms).
     */
    updateTimerDisplay(remainingMs) {
        const timerTextEl = this.el.querySelector("span");
        const humanDuration = formatDuration(remainingMs / 1000, true);
        const str = _t("in %s", humanDuration);
        if (str !== timerTextEl.textContent) {
            timerTextEl.textContent = str;
        }
    }
}

registry
    .category("public.interactions")
    .add(
        "website_event_track.website_event_track_timer",
        WebsiteEventTrackTimer
    );
