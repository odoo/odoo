import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { withSequence } from "@html_editor/utils/resource";
import { localeCompare } from "@web/core/l10n/utils/collation";

export class TeamBoardPlugin extends Plugin {
    static id = "teamBoard";
    static dependencies = ["builderOptions", "blockTab"];

    resources = {
        builder_actions: {
            AddTeamBoardMemberAction,
            SortTeamBoardCardAction,
        },
        should_remove_overlay_options_predicates: (el) => el.matches(".s_team_board_card"),
        get_overlay_buttons: withSequence(4, {
            getButtons: this.getOverlayButtons.bind(this),
        }),
        remove_disabled_reason_providers: (el) => {
            if (el.matches(".s_team_board_col") && el.parentElement.children.length === 1) {
                return _t("You cannot remove the last card.");
            }
        },

        options_container_top_buttons_providers: (el) => {
            const buttons = [];
            if (el.matches(".s_team_board")) {
                buttons.push({
                    class: "oi oi-fw btn o-hb-btn btn-accent-color-hover",
                    icon: "add",
                    title: _t("Add Item"),
                    handler: (el) => this.addTeamBoard(el),
                });
            }
            return buttons;
        },
    };

    addTeamBoard(sectionEl) {
        const snippet = this.config.snippetModel.getOriginalSnippet("s_team_board");
        const newSectionEl = snippet.content.cloneNode(true);
        sectionEl.after(newSectionEl);
        this.dependencies.builderOptions.setNextTarget(newSectionEl);
        this.dependencies.blockTab.scrollToDroppedSnippet(newSectionEl);
    }

    getOverlayButtons(target) {
        if (!target.matches(".s_team_board_col")) {
            return [];
        }
        return [
            {
                class: "oi oi-fw",
                icon: "star",
                title: _t("Set as priority"),
                handler: () => target.parentElement.prepend(target),
            },
        ];
    }
}

export class AddTeamBoardMemberAction extends BuilderAction {
    static id = "addTeamBoardMember";
    apply({ editingElement: rowEl }) {
        const columnEl = this.document.createElement("div");
        columnEl.className = "s_team_board_col col-lg-3 col-6 pb48";
        columnEl.innerHTML = `
            <div data-name="Card" class="s_card s_team_board_card o_card_img_top card cursor-pointer">
                <figure class="o_card_img_wrapper mb-0">
                    <img class="o_card_img card-img-top" src="/web/image/website.set_avatars_square_md_1"/>
                </figure>
                <div class="card-body">
                    <h3 class="card-title o_card_title">Ahmed Gamal</h3>
                    <p class="text-muted mb-3 o_job_position">Chief Executive Officer</p>
                    <p class="o_card_infos">Ahmed shapes product strategy and keeps execution aligned across teams.</p>
                </div>
                <button type="button" class="o_team_board_card_btn stretched-link p-0 border-0 bg-transparent" aria-haspopup="dialog" aria-label="Contact"/>
            </div>`;
        rowEl.append(columnEl);
    }
}

export class SortTeamBoardCardAction extends BuilderAction {
    static id = "sortTeamBoardCard";
    apply({ editingElement: rowEl }) {
        const columnEls = [...rowEl.children].filter((el) => el.querySelector(".s_card"));
        columnEls.sort((a, b) =>
            localeCompare(
                a.querySelector(".card-title").textContent.trim(),
                b.querySelector(".card-title").textContent.trim()
            )
        );
        for (const columnEl of columnEls) {
            rowEl.appendChild(columnEl);
        }
    }
}

registry.category("website-plugins").add(TeamBoardPlugin.id, TeamBoardPlugin);
