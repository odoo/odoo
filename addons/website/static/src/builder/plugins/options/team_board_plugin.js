import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { withSequence } from "@html_editor/utils/resource";
import { renderToElement } from "@web/core/utils/render";

export class TeamBoardAlphabeticSortAction extends BuilderAction {
    static id = "TeamBoardAlphabeticSort";
    apply({ editingElement }) {
        const row = editingElement.querySelector(" .container .row");
        const cards = Array.from(row.querySelectorAll(".o_team_board_card"));
        cards.sort((a, b) => {
            const titleA = a.querySelector(".card-title")?.textContent.trim().toLowerCase();
            const titleB = b.querySelector(".card-title")?.textContent.trim().toLowerCase();
            return titleA.localeCompare(titleB);
        });
        cards.forEach((card) => row.appendChild(card));
    }
}

export class TeamBoardAddMemberAction extends BuilderAction {
    static id = "TeamBoardAddMember";
    apply({ editingElement }) {
        const row = editingElement.querySelector(" .container .row");
        const lastCard = editingElement.querySelector(".o_team_board_card:last-child");
        const clone = lastCard.cloneNode(true);
        row.appendChild(clone);
    }
}

export class TeamBoardPlugin extends Plugin {
    static id = "teamBoardPlugin";

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
                accept: ".s_team_board_card",
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

    addMemberCard(el) {
        console.log("I HAVE BEEN CALLED GREAT NEWS YEEEE", el);
        const row = el.querySelector(" .container .row");
        const newMember = renderToElement("website.team_board.member_card", {});
        row.appendChild(newMember);
        newMember.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
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
                handler: this.addMemberCard.bind(this),
            },
        ];
    }
}

registry.category("website-plugins").add(TeamBoardPlugin.id, TeamBoardPlugin);
