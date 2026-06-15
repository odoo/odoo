import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class TeamBoardFavoritePlugin extends Plugin {
    static id = "teamBoardFavorite";
    resources = {
        get_overlay_buttons: withSequence(1, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
    };

    getActiveOverlayButtons(target) {
        if (!target.matches(".s_team_board .s_team_board_member_card")) {
            return [];
        }

        return [
            {
                class: "fa fa-star",
                title: _t("Favorite Member"),
                handler: () => target.parentElement.prepend(target),
            },
        ];
    }
}

registry.category("website-plugins").add(TeamBoardFavoritePlugin.id, TeamBoardFavoritePlugin);
