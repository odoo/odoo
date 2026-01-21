import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { AddSnippetDialogSandboxed } from "./snippet_viewer/add_snippet_dialog";
import { registry } from "@web/core/registry";

export class MassMailingSnippetModel extends SnippetModel {
    cleanSnippetForSave(snippetCopyEl, cleanForSaveHandlers) {
        super.cleanSnippetForSave(snippetCopyEl, cleanForSaveHandlers);
        const dynamicPlaceholders = snippetCopyEl.querySelectorAll("t[t-out]");
        dynamicPlaceholders.forEach((placeholderEl) => {
            const placeholderString =
                placeholderEl.innerText || placeholderEl.getAttribute("t-out");
            placeholderEl.before(placeholderString);
            placeholderEl.remove();
        });
        snippetCopyEl.removeAttribute("data-filter-domain");
    }
    getTechnicalUsage() {
        return "mass_mailing";
    }
    getAddSnippetDialogClass() {
        return AddSnippetDialogSandboxed;
    }
}

registry
    .category("html_builder.snippetsModel")
    .add("mass_mailing.email_designer_snippets", MassMailingSnippetModel);
