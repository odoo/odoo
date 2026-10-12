import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {BuilderAction} from "@html_builder/core/builder_action";
import { withSequence } from "@html_editor/utils/resource";

export class TeamBoardPlugin extends Plugin {
    static id = "teamBoard";

    resources = {
        builder_actions: {
            SortTeamBoardCard,
        },
        get_overlay_buttons: withSequence(4, {
            getButtons: this.getOverlayButtons.bind(this),
        }),
        remove_disabled_reason_providers: (el) => {
            const teamBoard = el.closest(".s_team_board");

            if (!teamBoard || el === teamBoard) {
                return;
            }

            const remainingCards = [...teamBoard.querySelectorAll(".s_team_board_card")].filter(
                (card) => !el.contains(card)
            );
            if (!remainingCards.length) {
                return _t("You cannot remove the last card.");
            }
        },
    };

    getOverlayButtons(target) {
        const column = target.closest(".s_team_board_col");
        if (!column || !target.matches(`${".s_team_board_col"}, ${".s_team_board_card"}`)) {
            return [];
        }
        const isPriority = column.classList.contains("o_team_board_priority");
        return [
            {
                class: isPriority ? "oi oi-fw oi-filled" : "oi oi-fw",
                icon: "star",
                title: isPriority ? _t("Remove priority") : _t("Set as priority"),
                handler: () => this.togglePriority(column),
            },
        ];
    }

    togglePriority(column) {
        const row = column.parentElement;

        if (column.classList.contains("o_team_board_priority")) {
            column.classList.remove("o_team_board_priority");
            const Elements = [...row.children].filter((el) => el !== column);
            const refEl = Elements[column.dataset.originalIndex];
            if (refEl) {
                refEl.before(column);
            } else {
                row.append(column);
            }
            delete column.dataset.originalIndex;
        } else {
            column.dataset.originalIndex = [...row.children].indexOf(column);
            column.classList.add("o_team_board_priority");
            row.prepend(column);
        }
    }
}

export class SortTeamBoardCard extends BuilderAction {
    static id = "sortTeamBoardCard";
    apply({editingElement}){
        const row = editingElement.querySelector(".row");
        if(!row ) {
            return
        }
        const names = [...row.children].filter((el) => el.querySelector(".s_card"));

        names.sort((a, b) => {
            const nameA = a.querySelector(".card-title")?.textContent.trim() || "";
            const nameB = b.querySelector(".card-title")?.textContent.trim() || "";

            return nameA.localeCompare(nameB);
        });

        for (const name of names) {
            row.appendChild(name);
        }

    }
}

registry.category("website-plugins").add(TeamBoardPlugin.id, TeamBoardPlugin);
