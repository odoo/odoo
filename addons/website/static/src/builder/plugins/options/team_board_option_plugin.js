import { _t } from "@web/core/l10n/translation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const MEMBER_SELECTOR = '.container > .row > [data-name="Team Member"]';

export class TeamBoardOptionPlugin extends Plugin {
    static id = "teamBoardOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            AddTeamMemberAction,
            SortTeamMembersAlphabeticallyAction,
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
        const memberEls = [...rowEl.querySelectorAll(':scope > [data-name="Team Member"]')];
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
