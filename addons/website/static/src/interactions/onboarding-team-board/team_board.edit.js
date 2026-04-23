import { registry } from "@web/core/registry";
import { TeamBoard } from "./team_board";

const TeamBoardEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            ".s_team_board_member_button": {
                ...this.dynamicContent[".s_team_board_member_button"],
                "t-att-class": () => ({ "pe-none": true }),
                "t-att-tabindex": () => "-1",
                "t-att-aria-hidden": () => "true",
            },
        };

        onMemberClick() {}
    };

registry.category("public.interactions.edit").add("website.team_board", {
    Interaction: TeamBoard,
    mixin: TeamBoardEdit,
});
