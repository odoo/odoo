import { registry } from "@web/core/registry";
import { TeamBoard } from "./team_board";

const TeamBoardEdit = (I) =>
    class extends I {
        dynamicContent = {
            ".s_team_board_member_card": {
                "t-att-data-bs-toggle": () => undefined,
                "t-att-data-bs-target": () => undefined,
            },
        };
    };

registry.category("public.interactions.edit").add("website.s_team_board", {
    Interaction: TeamBoard,
    mixin: TeamBoardEdit,
});
