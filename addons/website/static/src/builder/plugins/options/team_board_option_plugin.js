import { _t } from "@web/core/l10n/translation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { TeamBoardHeaderMiddleButtons } from "./team_board_header_buttons";

const MEMBER_SELECTOR = '.container > .row > [data-name="Team Member"]';

export class TeamBoardOptionPlugin extends Plugin {
    static id = "teamBoardOption";
    static dependencies = ["builderOptions", "blockTab", "history"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            AddTeamMemberAction,
            SortTeamMembersAlphabeticallyAction,
        },
        builder_header_middle_buttons: {
            Component: TeamBoardHeaderMiddleButtons,
            selector: ".s_team_board",
            props: {
                addBoard: this.addBoard.bind(this),
            },
        },
        dropzone_selectors: {
            selector: ".s_team_board",
            excludeAncestor: ".s_team_board, .s_popup, .s_table_of_content",
        },
        remove_disabled_reason_providers: (el) => {
            if (this.isLastTeamBoardCard(el)) {
                return _t("You cannot remove the last member.");
            }
        },
    };

    isLastTeamBoardCard(el) {
        const teamBoardEl = el.closest(".s_team_board");
        const isMemberElement = el.matches(".s_card") || el.matches('[data-name="Team Member"]');
        if (!teamBoardEl || !isMemberElement) {
            return false;
        }
        return teamBoardEl.querySelectorAll("[data-name='Team Member']").length === 1;
    }

    async addBoard(editingElement) {
        const snippet = this.config.snippetModel.getOriginalSnippet("s_team_board");
        if (!snippet) {
            return;
        }
        const newEl = snippet.content.cloneNode(true);
        editingElement.insertAdjacentElement("afterend", newEl);
        const cancelInsertion = this.dependencies.history.makeSavePoint();
        this.dependencies.builderOptions.setNextTarget(newEl);
        await this.dependencies.blockTab.processDroppedSnippet(newEl, cancelInsertion);
    }
}

export class AddTeamMemberAction extends BuilderAction {
    static id = "addTeamMember";
    static dependencies = ["clone", "history"];
    async apply({ editingElement }) {
        const lastMemberEl = editingElement.querySelector(`${MEMBER_SELECTOR}:last-of-type`);
        if (!lastMemberEl) {
            return;
        }
        const cloneEl = await this.dependencies.clone.cloneElement(lastMemberEl, {
            scrollToClone: true,
        });
        const nameEl = cloneEl.querySelector(".card-title");
        const roleEl = cloneEl.querySelector(".card-body p.text-muted");
        const bioEl = cloneEl.querySelector(".card-body > p:not(.text-muted)");
        if (nameEl) {
            nameEl.textContent = _t("New member");
        }
        if (roleEl) {
            roleEl.textContent = _t("Role");
        }
        if (bioEl) {
            bioEl.textContent = _t("Short bio about this person.");
        }
        this.dependencies.history.addStep();
    }
}

export class SortTeamMembersAlphabeticallyAction extends BuilderAction {
    static id = "sortTeamMembersAlphabetically";
    static dependencies = ["history"];
    apply({ editingElement }) {
        const rowEl = editingElement.querySelector(":scope > .container > .row");
        if (!rowEl) {
            return;
        }
        const memberEls = [...editingElement.querySelectorAll(MEMBER_SELECTOR)];
        if (memberEls.length < 2) {
            return;
        }
        memberEls.sort((a, b) => {
            const aName = a.querySelector(".card-title")?.textContent.trim() ?? "";
            const bName = b.querySelector(".card-title")?.textContent.trim() ?? "";
            return aName.localeCompare(bName);
        });
        memberEls.forEach((el) => rowEl.append(el));
        this.dependencies.history.addStep();
    }
}

registry.category("website-plugins").add(TeamBoardOptionPlugin.id, TeamBoardOptionPlugin);
