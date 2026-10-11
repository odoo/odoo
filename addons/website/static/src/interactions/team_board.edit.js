import { registry } from "@web/core/registry";
import { patchDynamicContent } from "@web/public/utils";
import { TeamBoard } from "./team_board";
export const TeamBoardEdit = (I) =>
    class extends I {
        setup() {
            patchDynamicContent(this.dynamicContent, {
                ".s_team_board_card": {
                    "t-on-click": undefined,
                    "t-on-keydown": undefined,
                    "t-att-role": undefined,
                    "t-att-tabindex": undefined,
                    "t-att-aria-haspopup": undefined,
                },
            });
            super.setup();
        }
    };
registry.category("public.interactions.edit").add("website.team_board", {
    Interaction: TeamBoard,
    mixin: TeamBoardEdit,
});
