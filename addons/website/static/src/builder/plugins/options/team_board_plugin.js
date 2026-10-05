import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class TeamBoardPlugin extends Plugin {
    static id = "teamBoardPlugin";

    resources = {
        remove_disabled_reason_providers: (el) => {
            if (el.matches(".o_team_board_card:only-child")) {
                return _t("You cannot remove the last item.");
            }
        },
        dropzone_selectors: [
            {
                selector: ".s_team_board",
                excludeAncestor:
                    ".s_team_board, .s_table_of_content, .s_table_of_content_content, .s_popup, .o_popup_modal, .modal",
            },
            {
                selector: ".s_team_board .row",
                accept: ".s_team_board_card",
            },
        ],
    };
}

registry.category("website-plugins").add(TeamBoardPlugin.id, TeamBoardPlugin);
