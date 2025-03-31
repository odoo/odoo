import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

import { Quiz } from "@website_event_track_quiz/interactions/quiz";

patch(Quiz.prototype, {
    async willStart() {
        await super.willStart();
        return this.getTrackSuggestion();
    },
    async submitQuiz() {
        const data = await super.submitQuiz();
        if (data.quiz_completed) {
            const nextTrackEl = this.el.querySelector(".o_quiz_js_quiz_next_track");
            nextTrackEl.classList.remove("btn-light");
            nextTrackEl.classList.add("btn-secondary");
        }
        return data;
    },
    async getTrackSuggestion() {
        const suggestion = await this.waitFor(
            rpc("/event_track/get_track_suggestion", {
                track_id: this.track.id,
            })
        );
        this.nextSuggestion = suggestion;
    },
});
