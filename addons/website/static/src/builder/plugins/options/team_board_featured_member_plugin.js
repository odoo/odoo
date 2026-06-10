import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class TeamBoardFeaturedMemberPlugin extends Plugin {
    static id = "teamBoardFeaturedMemberPlugin";
    resources = {
        get_overlay_buttons: withSequence(15, {
            getButtons: this.getOverlayButtons.bind(this),
        }),
    };

    getOverlayButtons(target) {
        if (!target.matches(".o_team_board_card_container > .s_card")) {
            return [];
        }

        return [
            {
                class: "fa fa-star o_move_to_top_button",
                title: _t("Move to top"),
                handler: () => this.moveToTop(target),
            },
        ];
    }

    moveToTop(el) {
        const parent = el.parentElement;
        if (!parent || parent.firstElementChild === el) {
            return;
        }

        parent.prepend(el);
    }
}

registry
    .category("website-plugins")
    .add(TeamBoardFeaturedMemberPlugin.id, TeamBoardFeaturedMemberPlugin);
