import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { isMediaElement } from "@html_editor/utils/dom_info";

class CompanyTeamPlugin extends Plugin {
    static id = "companyTeam";
    resources = {
        extra_contenteditable_handlers: this.extraContentEditableHandlers.bind(this),
    };

    extraContentEditableHandlers(filteredContentEditableEls) {
        // To fix db in stable
        const extraContentEditableEls = filteredContentEditableEls.flatMap(
            (filteredContentEditableEl) => [
                ...filteredContentEditableEl.querySelectorAll(".s_company_team .o_not_editable *"),
            ]
        );
        return extraContentEditableEls.filter((el) => isMediaElement(el) || el.tagName === "IMG");
    }
}

registry.category("website-plugins").add(CompanyTeamPlugin.id, CompanyTeamPlugin);
