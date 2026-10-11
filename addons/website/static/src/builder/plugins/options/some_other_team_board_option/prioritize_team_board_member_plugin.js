import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";

export class PrioritizeTeamBoardMemberPlugin extends Plugin {
    static id = "prioritizeTeamBoardMemberPlugin";

    resources = {
        get_overlay_buttons: withSequence(2, {
            getButtons: this.getOverlayButtons.bind(this),
        }),
    };

    getOverlayButtons(target) {
        if (!this.isTeamBoardCard(target)) {
            return [];
        }
        return [
            {
                class: "oe_snippet_prioritize text-warning oi",
                icon: "star",
                title: _t("Prioritize"),
                handler: () => {
                    this.prioritizeCard(target);
                },
            },
        ];
    }

    isTeamBoardCard(target) {
        return Boolean(target.matches(".o_team_board_card"));
    }

    prioritizeCard(target) {
        const row = target.closest(".row");
        row.prepend(target);
    }
}

registry
    .category("website-plugins")
    .add(PrioritizeTeamBoardMemberPlugin.id, PrioritizeTeamBoardMemberPlugin);
