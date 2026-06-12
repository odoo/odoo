import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { localeCompare } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { TeamBoardOptionHeaderMiddleButtons } from "./team_board_option_header_middle_buttons";

export class TeamBoardOptionPlugin extends Plugin {
    static id = "teamBoardOption";
    static dependencies = ["dom", "history", "builderOptions"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: {
            Component: TeamBoardOptionHeaderMiddleButtons,
            selector: ".s_team_board",
            props: {
                createNewTeamBoard: () => {
                    const snippet = this.config.snippetModel.getSnippetByName(
                        "snippet_structure",
                        "s_team_board"
                    );

                    const contentEl = snippet.content.cloneNode(true);
                    this.editable.querySelector("#wrap").appendChild(contentEl);

                    this.dependencies.builderOptions.setNextTarget(contentEl);
                    this.dependencies.history.commit();

                    contentEl.scrollIntoView();
                },
            },
        },
        remove_disabled_reason_providers: (el) => {
            if (this.isLastTeamMemberItem(el)) {
                return _t("You cannot remove this elemant");
            }
        },
        dropzone_selectors: [
            {
                selector: ".s_team_board",
                exclude: ".s_popup, s_table_of_content",
            },
            {
                selector: ".o_team_board_col",
                dropIn: ".o_team_board_row_wrapper",
                dropNear: ".o_team_board_col",
                dropLockWithin: ".s_team_board",
            },
        ],
        builder_actions: {
            AddTeamBoardCardAction,
            SetTeamBoardLayoutAction,
            SortTeamBoardAction,
        },
    };

    isLastTeamMemberItem(el) {
        if (el.matches(".col:only-child")) {
            return true;
        }
        return false;
    }
}

export class AddTeamBoardCardAction extends BuilderAction {
    static id = "addTeamBoardCardAction";
    static dependencies = ["teamBoardOption"];

    apply({ editingElement }) {
        const rowEl = editingElement.querySelector(".o_team_board_row");

        const newCardEl = renderToElement("website.s_team_board_card");

        rowEl.appendChild(newCardEl);
    }
}

export class SortTeamBoardAction extends BuilderAction {
    static id = "sortTeamBoard";
    static dependencies = ["teamBoardOption"];

    apply({ editingElement }) {
        const rowEl = editingElement.querySelector(".o_team_board_row");

        [...rowEl.children]
            .sort((colAEl, colBEl) => localeCompare(colAEl.innerText, colBEl.innerText))
            .forEach((colEl) => rowEl.appendChild(colEl));
    }
}

export class SetTeamBoardLayoutAction extends BuilderAction {
    static id = "setTeamBoardLayout";
    static dependencies = ["teamBoardOption", "cardImageOption"];

    apply({ editingElement, params: { mainParam } }) {
        const cardEls = editingElement.querySelectorAll(".s_card");
        const imageEls = editingElement.querySelectorAll(".o_card_img");

        if (mainParam === "list") {
            imageEls.forEach((imageEl) => {
                imageEl.classList.add("rounded-start");
            });
            cardEls.forEach((cardEl) => {
                cardEl.classList.add("flex-lg-row");
                cardEl.classList.add("o_card_img_horizontal");
                this.dependencies.cardImageOption.adaptRatio(cardEl, "rounded-start");
            });
        }
    }

    clean({ editingElement, params: { mainParam } }) {
        const cardEls = editingElement.querySelectorAll(".s_card");
        const imageEls = editingElement.querySelectorAll(".o_card_img");

        if (mainParam === "list") {
            cardEls.forEach((cardEl) => {
                cardEl.classList.remove("flex-lg-row");
                cardEl.classList.remove("o_card_img_horizontal");
            });
            imageEls.forEach((imageEl) => {
                imageEl.classList.remove("rounded-start");
            });
        }
    }
}

registry.category("website-plugins").add(TeamBoardOptionPlugin.id, TeamBoardOptionPlugin);
