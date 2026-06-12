import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class TeamBoardExtrasPlugin extends Plugin {
    static id = "TeamBoardExtras";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        get_overlay_buttons: withSequence(20, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
    };

    getActiveOverlayButtons(target) {
        if (!target.matches(".s_team_board_member")) {
            return [];
        }
        return [
            {
                class: "fa fa-fw fa-star",
                title: _t("Feature this member"),
                handler: () => {
                    target.parentElement.prepend(target);
                },
            },
        ];
    }
}

registry.category("website-plugins").add(TeamBoardExtrasPlugin.id, TeamBoardExtrasPlugin);
