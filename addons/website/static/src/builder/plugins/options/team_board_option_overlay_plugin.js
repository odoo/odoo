import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

function isTeamBoardCard(el) {
    return el.matches(".o_team_board_col");
}

export class TeamBoardOptionOverlayPlugin extends Plugin {
    static id = "teamBoardOptionOverlay";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        has_overlay_options: { hasOption: (el) => isTeamBoardCard(el) },
        get_overlay_buttons: withSequence(10, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
    };

    getActiveOverlayButtons(target) {
        if (!isTeamBoardCard(target)) {
            return [];
        }

        return [
            {
                class: "fa fa-star",
                title: _t("Move to first place"),
                handler: () => {
                    const row = target.closest(".o_team_board_row");
                    row.prepend(target);
                },
            },
        ];
    }
}

registry
    .category("website-plugins")
    .add(TeamBoardOptionOverlayPlugin.id, TeamBoardOptionOverlayPlugin);
