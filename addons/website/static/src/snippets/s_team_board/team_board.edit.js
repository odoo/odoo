import { registry } from "@web/core/registry";
import { TeamBoard } from "./team_board";

const TeamBoardEdit = (I) => 
    class extends I {
        _onClickCard() {
            return;
        }
    }

registry.category("public.interactions.edit").add("website.team_board", {
    Interaction: TeamBoard,
    mixin : TeamBoardEdit
});
