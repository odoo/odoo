import { _t } from "@web/core/l10n/translation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { localeCompare } from "@web/core/l10n/utils";

export class TeamBoardPlugin extends Plugin {
    static id = "teamBoard";
    static dependencies = ["builderOptions"];
    resources = {
        builder_actions: { SortTeamBoardMembersAction },
        remove_disabled_reason_providers: (el) => {
            if (
                el.matches(".s_team_board_member") &&
                el.closest(".s_team_board")?.querySelectorAll(".s_team_board_member").length <= 1
            ) {
                return _t("At least one team member is required.");
            }
        },
        dropzone_selectors: {
            selector: ".s_team_board",
            excludeAncestor: ".s_team_board, .s_popup, .s_table_of_content",
        },
        options_container_top_buttons_providers: this.getOptionsContainerTopButtons.bind(this),
    };

    getOptionsContainerTopButtons(el) {
        if (!el.matches(".s_team_board")) {
            return [];
        }

        return [{
            class: "oi oi-fw btn o-hb-btn btn-accent-color-hover",
            icon: "add",
            title: _t("Add new"),
            handler: () => {
                const snippet = this.config.snippetModel.getOriginalSnippet("s_team_board");
                const clonedEl = snippet.content.cloneNode(true);

                el.after(clonedEl);

                this.dependencies.builderOptions.setNextTarget(clonedEl);
                const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
                clonedEl.scrollIntoView({ behavior: prefersReducedMotion ? "instant" : "smooth" });
            },
        }];
    }
}

export class SortTeamBoardMembersAction extends BuilderAction {
    static id = "sortTeamBoardMembers";
    apply({ editingElement }) {
        const row = editingElement.querySelector(".row");
        const getName = (el) => el.querySelector(".card-title")?.textContent.trim() ?? "";
        const sortedEls = [...row.children].sort((a, b) => localeCompare(getName(a), getName(b)));
        row.append(...sortedEls);
    }
}

registry.category("website-plugins").add(TeamBoardPlugin.id, TeamBoardPlugin);
