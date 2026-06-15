import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { localeCompare } from "@web/core/l10n/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { generateHTMLId } from "@web/core/utils/strings";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class TeamBoardOptionPlugin extends Plugin {
    static id = "teamBoardOption";
    static dependencies = ["builderOptions"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: [
            {
                selector: ".s_team_board",
                excludeAncestor: ".s_team_board, .s_popup, .s_table_of_content",
            },
        ],
        options_container_top_buttons_providers: this.getButtons.bind(this),
        remove_disabled_reason_providers: (el) => {
            if (el.matches(".s_card:only-child")) {
                return _t("You cannot remove the last card.");
            }
        },
        builder_actions: {
            SortTeamBoardAlphabetically,
            AddTeamBoardMember,
        },
        on_will_save_handlers: (el) => {
            for (const teamBoardEl of selectElements(el, ".s_team_board")) {
                const boardCardEls = teamBoardEl.querySelectorAll(
                    ".o_team_board_card_container > .card:not([data-bs-toggle])"
                );

                const modalid = teamBoardEl.querySelector(".modal").id;
                for (const cardEl of boardCardEls) {
                    cardEl.setAttribute("data-bs-toggle", "modal");
                    cardEl.setAttribute("data-bs-target", `#${modalid}`);
                }
            }
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => this.assignModalId(snippetEl),
        on_cloned_handlers: ({ cloneEl }) => this.assignModalId(cloneEl),
    };

    getButtons() {
        return [
            {
                class: "create_new_team_board_option fa fa-plus",
                title: "Add new",
                handler: (el) => {
                    const snippet = this.config.snippetModel.getOriginalSnippet("s_team_board");
                    const cloned_el = snippet.content.cloneNode(true);
                    el.parentElement.append(cloned_el);

                    this.dependencies.builderOptions.setNextTarget(cloned_el);
                    cloned_el.scrollIntoView({ behavior: "smooth" });
                },
            },
        ];
    }

    assignModalId(boardEl) {
        if (!boardEl.matches(".s_team_board")) {
            return;
        }

        const elid = generateHTMLId();
        boardEl.querySelector(".modal").id = elid;
        for (const il of boardEl.querySelectorAll(".card")) {
            il.setAttribute("data-bs-target", `#${elid}`);
        }
    }
}

export class SortTeamBoardAlphabetically extends BuilderAction {
    static id = "sortTeamBoardAlphabetically";

    apply({ editingElement }) {
        const cardsContainer = editingElement.querySelector(".o_team_board_card_container");
        const sortedCards = [...editingElement.querySelectorAll(".card")].sort((a, b) => {
            const a_name = a.querySelector(".o_team_board_card_name")?.textContent;
            const b_name = b.querySelector(".o_team_board_card_name")?.textContent;
            return localeCompare(a_name, b_name);
        });

        cardsContainer.replaceChildren(...sortedCards);
    }
}

export class AddTeamBoardMember extends BuilderAction {
    static id = "addTeamBoardMember";
    static dependencies = ["clone"];

    async apply({ editingElement }) {
        const cardTemplateEl = editingElement.querySelector(".card:last-child");
        await this.dependencies.clone.cloneElement(cardTemplateEl, {
            activateClone: false,
        });
    }
}

registry.category("website-plugins").add(TeamBoardOptionPlugin.id, TeamBoardOptionPlugin);
