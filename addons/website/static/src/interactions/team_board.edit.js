import { registry } from "@web/core/registry";
import { patchDynamicContent } from "@web/public/utils";
import { TeamBoard } from "./team_board";
export const TeamBoardEdit = (I) =>
    class extends I {
        setup() {
            patchDynamicContent(this.dynamicContent, {
                ".s_team_board_card .o_team_board_card_btn": {
                    "t-on-click": () => {},
                    "t-att-class": () => ({ "d-none": true }),
                },
            });
            super.setup();
        }
    };
registry.category("public.interactions.edit").add("website.team_board", {
    Interaction: TeamBoard,
    mixin: TeamBoardEdit,
});
