
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class TeamBoardCardTopPlugin extends Plugin {
    static id = "teamBoardCardTop";

    resources = {
        get_overlay_buttons: {
            getButtons: (el) => {
                if (
                    !el.matches(".s_team_board_member") ||
                    el.parentElement.matches(".o_grid_mode")
                ) {
                    return [];
                }

                return [{
                    class: "oi oi-fw fw-bolder",
                    icon: "arrow_upward",
                    title: _t("Move to first position"),
                    handler: () => el.parentElement.prepend(el),
                }];
            },
        },
    };
}

registry.category("website-plugins").add(TeamBoardCardTopPlugin.id, TeamBoardCardTopPlugin);
