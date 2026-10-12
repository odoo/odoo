import { Interaction } from "@web/public/interaction";
import { redirect } from "@web/core/utils/urls";
import { registry } from "@web/core/registry";

export class WebsiteEventTrackSuggestion extends Interaction {
    static selector = ".owevent_track_video_suggestion";
    dynamicContent = {
        ".owevent_track_suggestion_next": {
            "t-on-click": this.onNextTrackClick,
            "t-att-class": () => ({ invisible: !this.nextVisible }),
        },
        ".owevent_track_suggestion_close": {
            "t-on-click": this.onCloseClick,
        },
        ".owevent_track_suggestion_replay": {
            "t-on-click": this.onReplayClick,
        },
    };

    setup() {
        this.nextVisible = true;
        this.trackUrl = this.el.dataset.websiteUrl;
        this.timerEl = this.el.querySelector(".owevent_track_suggestion_timer_text");
        this.timer = parseInt(this.timerEl.textContent);
        this.timerInterval = setInterval(this.updateTimer.bind(this), 1000);
    }

    onReplayClick() {
        this.el.dispatchEvent(new Event("replay"));
        clearInterval(this.timerInterval);
        this.el.remove();
    }

    onCloseClick(event) {
        event.stopPropagation();
        clearInterval(this.timerInterval);
        this.nextVisible = false;
    }

    onNextTrackClick() {
        redirect(this.trackUrl);
    }

    updateTimer() {
        if (this.timer > 1) {
            this.timer--;
            this.timerEl.textContent = ` ${this.timer}`;
        } else {
            redirect(this.trackUrl);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event_track_live.WebsiteEventTrackSuggestion", WebsiteEventTrackSuggestion);
