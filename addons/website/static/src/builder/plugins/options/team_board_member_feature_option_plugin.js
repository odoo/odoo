import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class TeamBoardFeatureMemberOptionPlugin extends Plugin {
    static id = "teamBoardFeatureMemberOption";
    static dependencies = ["history"];

    resources = {
        get_overlay_buttons: withSequence(100, {
            getButtons: this.getFeatureMemberButton.bind(this),
        }),
    };

    getFeatureMemberButton(target) {
        if (!isTeamBoardMember(target)) {
            this.overlayTarget = null;
            return [];
        }
        this.overlayTarget = target;
        return [
            {
                class: "fa fa-fw fa-star",
                title: _t("Feature member"),
                handler: this.featureMember.bind(this),
            },
        ];
    }

    featureMember() {
        const rowEl = this.overlayTarget.parentElement;
        if (!rowEl || rowEl.firstElementChild === this.overlayTarget) {
            return;
        }
        rowEl.prepend(this.overlayTarget);
        this.dependencies.history.addStep();
    }
}

function isTeamBoardMember(el) {
    return el.matches('[data-name="Team Member"]') && !!el.closest(".s_team_board");
}

registry
    .category("website-plugins")
    .add(TeamBoardFeatureMemberOptionPlugin.id, TeamBoardFeatureMemberOptionPlugin);
