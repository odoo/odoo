import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Leaderboard extends Interaction {
    static selector = ".o_wevent_quiz_leaderboard .o_wevent_quiz_scroll_to";

    start() {
        this.el.scrollIntoView({ behavior: "smooth" });
    }
}

registry
    .category("public.interactions")
    .add("website_event_track_quiz.leaderboard", Leaderboard);
