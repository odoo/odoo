import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class TeamBoardOptionPlugin extends Plugin {
    static id = "TeamBoardOption";
    static dependencies = ["builderOptions"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SortTeamBoardMembersAlphabeticallyAction,
        },
        dropzone_selectors: {
            selector: ".s_team_board",
            excludeAncestor: ".s_team_board, .s_popup, .s_table_of_content",
        },
        options_container_top_buttons_providers: this.getOptionsContainerTopButtons.bind(this),
        remove_disabled_reason_providers: this.getRemoveDisabledReason.bind(this),
    };

    getOptionsContainerTopButtons(el) {
        if (!el.matches(".s_team_board")) {
            return [];
        }
        return [
            {
                class: "fa fa-fw fa-plus btn o-hb-btn btn-success-color-hover",
                title: _t("Add new team board"),
                handler: this.addTeamBoard.bind(this),
            },
        ];
    }

    addTeamBoard(teamBoardEl) {
        const newTeamBoardEl = this.config.snippetModel
            .getOriginalSnippet("s_team_board")
            .content.cloneNode(true);
        this.config.snippetModel.updateSnippetContent(newTeamBoardEl);
        teamBoardEl.after(newTeamBoardEl);
        this.dependencies.builderOptions.setNextTarget(newTeamBoardEl);
        newTeamBoardEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    getRemoveDisabledReason(el) {
        if (
            el.matches(".s_team_board_member") &&
            el.parentElement?.querySelectorAll(".s_team_board_member").length <= 1
        ) {
            return _t("Keep at least one member.");
        }
    }
}

export class SortTeamBoardMembersAlphabeticallyAction extends BuilderAction {
    static id = "sortTeamBoardMembersAlphabetically";

    apply({ editingElement }) {
        const teamBoardEl = editingElement.closest(".s_team_board");
        const membersEl = teamBoardEl?.querySelector(".s_team_board_members");
        if (!membersEl) {
            return;
        }
        const memberEls = [...membersEl.children].filter((el) =>
            el.classList.contains("s_team_board_member")
        );
        memberEls
            .sort((memberAEl, memberBEl) => {
                const memberAName =
                    memberAEl.querySelector(".card-title")?.textContent?.trim() || "";
                const memberBName =
                    memberBEl.querySelector(".card-title")?.textContent?.trim() || "";
                return memberAName.localeCompare(memberBName, undefined, { sensitivity: "base" });
            })
            .forEach((memberEl) => membersEl.appendChild(memberEl));
    }
}

registry.category("website-plugins").add(TeamBoardOptionPlugin.id, TeamBoardOptionPlugin);
