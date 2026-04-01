import { WebsiteEventTrackSuggestion } from "@website_event_track_live/interactions/website_event_track_suggestion";
import { patch } from "@web/core/utils/patch";

patch(WebsiteEventTrackSuggestion.prototype, {
    setup() {
        this.dynamicSelectors = {
            ...this.dynamicSelectors,
            _quiz: () => document.querySelector(".o_quiz_js_quiz_container"),
        };
        this.dynamicContent = {
            ...this.dynamicContent,
            ".owevent_track_suggestion_quiz": {
                "t-on-click": this.onQuizClick,
            },
            _quiz: {
                "t-att-class": () => ({ "d-none": !this.showQuiz }),
            },
        };
        super.setup();
        this.showQuiz = false;
    },
    onQuizClick() {
        this.showQuiz = true;
        clearInterval(this.timerInterval);
        this.el.querySelector(".owevent_track_suggestion_timer_text_wrapper")?.remove();
    },
});
