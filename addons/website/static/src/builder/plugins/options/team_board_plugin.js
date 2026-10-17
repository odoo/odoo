import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { withSequence } from "@html_editor/utils/resource";

export class TeamBoardAlphabeticSortAction extends BuilderAction {
    static id = "teamBoardAlphabeticSort";
    apply({ editingElement }) {
        const rowEl = editingElement.querySelector(" .container .row");
        const cardEls = Array.from(rowEl.querySelectorAll(".o_team_board_card"));
        cardEls.sort((a, b) => {
            const titleA = a.querySelector(".card-title")?.textContent.trim().toLowerCase();
            const titleB = b.querySelector(".card-title")?.textContent.trim().toLowerCase();
            return titleA.localeCompare(titleB);
        });
        rowEl.append(...cardEls);
    }
}

export class TeamBoardAddMemberAction extends BuilderAction {
    static dependencies = ["clone"];

    static id = "teamBoardAddMember";
    async apply({ editingElement }) {
        const rowEl = editingElement.querySelector(" .container .row"); // nav item

        const lastCardEl = editingElement.querySelector(".o_team_board_card:last-child"); // activ pane
        const clonedEl = await this.dependencies.clone.cloneElement(lastCardEl);
        rowEl.appendChild(clonedEl);
    }
}

export class TeamBoardPlugin extends Plugin {
    static id = "teamBoardPlugin";
    static dependencies = ["builderOptions"];

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
                dropIn: ".s_team_board_card",
            },
        ],
        builder_actions: {
            TeamBoardAlphabeticSortAction,
            TeamBoardAddMemberAction,
        },
        options_container_top_buttons_providers: withSequence(
            20,
            this.getOptionsContainerTopButtons.bind(this)
        ),
    };

    addTeamBoard(el) {
        const snippet = this.config.snippetModel.getOriginalSnippet("s_team_board");
        const clonedEl = snippet.content.cloneNode(true);
        el.after(clonedEl);
        this.dependencies.builderOptions.setNextTarget(clonedEl);
    }

    getOptionsContainerTopButtons(el) {
        if (!el.classList.contains("s_team_board")) {
            return [];
        }
        return [
            {
                class: "oi oi-fw o_we_hover_warning btn o-hb-btn btn-global-color-hover",
                icon: "add",
                title: _t("Add a new card memeber!"),
                handler: this.addTeamBoard.bind(this),
            },
        ];
    }
}

registry.category("website-plugins").add(TeamBoardPlugin.id, TeamBoardPlugin);
