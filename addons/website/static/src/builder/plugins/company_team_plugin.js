import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { isMediaElement } from "@html_editor/utils/dom_info";
import { selectElements } from "@html_editor/utils/dom_traversal";

class CompanyTeamPlugin extends Plugin {
    static id = "companyTeam";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        content_editable_providers: this.getEditableEls.bind(this),
    };

    getEditableEls(rootEl) {
        // To fix db in stable
        const contentEditableEls = [...selectElements(rootEl, ".s_company_team .o_not_editable *")];
        return contentEditableEls.filter((el) => isMediaElement(el) || el.tagName === "IMG");
    }
}

registry.category("website-plugins").add(CompanyTeamPlugin.id, CompanyTeamPlugin);
