import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class WebsiteEventTrackReplaySuggestion extends Interaction {
    static selector = ".owevent_track_replay_suggestion";
    dynamicContent = {
        ".owevent_track_suggestion_replay": {
            "t-on-click": this.onReplayClick,
        },
    };

    onReplayClick() {
        this.el.dispatchEvent(new Event("replay"));
        this.el.remove();
    }
}

registry
    .category("public.interactions")
    .add(
        "website_event_track_live.WebsiteEventTrackReplaySuggestion",
        WebsiteEventTrackReplaySuggestion
    );
