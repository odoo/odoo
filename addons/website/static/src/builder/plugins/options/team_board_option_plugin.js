import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

export class TeamBoardOptionPlugin extends Plugin {
    static id = "teamBoardOption";
    resources = {
        dropzone_selectors: [
            {
                selector: ".s_team_board",
                excludeAncestor: ".s_team_board, .s_popup, .s_table_of_content",
            },
        ],
        remove_disabled_reason_providers: (el) => {
            if (el.matches(".s_team_board_member_card:only-child")) {
                return _t("The last card may not be removed.");
            }
        },
        builder_actions: {
            AddMemberAction,
            SortMemberAction,
        },
    };
}

export class AddMemberAction extends BuilderAction {
    static id = "addMember";

    setup() {
        this.canTimeout = false;
    }
    async apply({ editingElement: teamBoardEl }) {
        const memberEl = teamBoardEl.querySelector(".s_team_board_member_card");
        const copyMemberEl = memberEl.cloneNode(true);
        teamBoardEl.querySelector(".s_team_board_wrapper").appendChild(copyMemberEl);
    }
}

export class SortMemberAction extends BuilderAction {
    static id = "sortMember";
    static dependencies = ["teamBoardOption"];

    setup() {
        this.canTimeout = false;
    }

    async apply({ editingElement: teamBoardEl }) {
        const memberContainerEl = teamBoardEl.querySelector(".s_team_board_wrapper");
        const sortedEls = [...memberContainerEl.children].sort((a, b) =>
            a
                .querySelector(".o_team_board_name")
                .textContent.localeCompare(b.querySelector(".o_team_board_name").textContent)
        );
        memberContainerEl.replaceChildren(...sortedEls);
    }
}

registry.category("website-plugins").add(TeamBoardOptionPlugin.id, TeamBoardOptionPlugin);
