import { registry } from "@web/core/registry";
import { TeamBoard } from "./team_board.js";

const TeamBoardEdit = (I) =>
    class extends I {
        dynamicContent = {
            ".card": {
                "t-att-data-bs-toggle": () => undefined,
                "t-att-data-bs-target": () => undefined,
            },
        };
    };

registry.category("public.interactions.edit").add("awesome_website.image_comparison", {
    Interaction: TeamBoard,
    mixin: TeamBoardEdit,
});
