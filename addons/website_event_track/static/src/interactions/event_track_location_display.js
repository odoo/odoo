import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const REFRESH_INTERVAL = 30_000;
const FAILED_REFRESH_THRESHOLD = 3;
const BACKGROUND_CLASS = "o_wevent_location_display_has_background";
const BACKGROUND_PROPERTY = "--o-wevent-location-display-background-image";

export class EventTrackLocationDisplay extends Interaction {
    static selector = ".o_wevent_location_display";

    setup() {
        this.failedRefreshes = 0;
        this.lastUpdatedAt = new Date();
        this.scheduleRefresh();
    }

    scheduleRefresh() {
        this.refreshTimeout = this.waitForTimeout(async () => {
            await this.refreshContent();
            this.scheduleRefresh();
        }, REFRESH_INTERVAL);
    }

    destroy() {
        clearTimeout(this.refreshTimeout);
    }

    async refreshContent() {
        try {
            const html = await this.waitFor(rpc(this.el.dataset.refreshUrl, {}, { silent: true }));
            const content = new DOMParser()
                .parseFromString(html.trim(), "text/html")
                .body.firstElementChild;
            const currentContent = this.el.querySelector(".o_wevent_location_display_content");
            this.updateBackground(content.dataset.backgroundImageUrl);
            this.updateCurrentTime(content.dataset.currentTime);
            this.insert(content, currentContent, "beforebegin", false);
            this.services["public.interactions"].stopInteractions(currentContent);
            currentContent.remove();
            const wasOffline = this.failedRefreshes >= FAILED_REFRESH_THRESHOLD;
            this.failedRefreshes = 0;
            this.lastUpdatedAt = new Date();
            if (wasOffline) {
                this.updateRefreshStatus();
            }
        } catch {
            // Keep the last successfully loaded schedule visible while offline.
            this.failedRefreshes++;
            if (this.failedRefreshes === FAILED_REFRESH_THRESHOLD) {
                this.updateRefreshStatus();
            }
        }
    }

    updateCurrentTime(currentTimeLabel) {
        const timeEl = this.el.querySelector(".o_wevent_location_display_now");
        if (timeEl && currentTimeLabel) {
            timeEl.textContent = currentTimeLabel;
        }
    }

    updateBackground(backgroundImageUrl) {
        this.el.classList.toggle(BACKGROUND_CLASS, Boolean(backgroundImageUrl));
        if (backgroundImageUrl) {
            this.el.style.setProperty(BACKGROUND_PROPERTY, `url(${backgroundImageUrl})`);
        } else {
            this.el.style.removeProperty(BACKGROUND_PROPERTY);
        }
    }

    updateRefreshStatus() {
        const status = this.el.querySelector(".o_wevent_location_display_refresh_status");
        if (!status) {
            return;
        }
        const isOffline = this.failedRefreshes >= FAILED_REFRESH_THRESHOLD;
        status.classList.toggle("d-none", !isOffline);
        if (!isOffline) {
            return;
        }
        const formattedTime = this.lastUpdatedAt.toLocaleTimeString([], { timeStyle: "short" });
        status.querySelector("time").textContent = formattedTime;
    }
}

registry.category("public.interactions").add(
    "website_event_track.event_track_location_display",
    EventTrackLocationDisplay
);
