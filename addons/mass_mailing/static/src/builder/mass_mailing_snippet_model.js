import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { AddSnippetDialogSandboxed } from "./snippet_viewer/add_snippet_dialog";
import { registry } from "@web/core/registry";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { user } from "@web/core/user";
import { nbsp } from "@web/core/utils/strings";

const { DateTime } = luxon;

export class MassMailingSnippetModel extends SnippetModel {
    cleanSnippetForSave(snippetCopyEl, cleanForSaveProcessors) {
        super.cleanSnippetForSave(snippetCopyEl, cleanForSaveProcessors);
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

    async completeSnippetsDocument(document, context) {
        if (this.getTechnicalUsage() != "mass_mailing") {
            return super.completeSnippetsDocument();
        }

        const globalValues = {
            // add base snippet context
            ...context,
            this: Object.create(context),
            user_id: {
                ...user,
                id: user.userId,
                company_id: user.defaultCompany,
            },
            company_id: {
                ...user.defaultCompany,
            },
            now: DateTime.now(),
            nbsp: nbsp,
        };

        const companyData = await this.orm.call("res.company", "get_mailing_snippet_info", [
            user.defaultCompany.id,
        ]);
        for (const [key, value] of Object.entries(companyData)) {
            globalValues["company_id"][key] = value;
        }
        const builtinMMSnippets = renderToFragment(this.snippetsName, globalValues);
        builtinMMSnippets.querySelectorAll("group[snippet-group]").forEach((el) => {
            const value = el.getAttribute("snippet-group");
            el.setAttribute("name", el.getAttribute("string"));
            el.dataset.oSnippetGroup = value;
            if (el.hasAttribute("thumbnail")) {
                el.dataset.oeThumbnail = el.getAttribute("thumbnail");
            }
            el.append(renderToElement("mass_mailing.s_snippet_group"));
        });
        builtinMMSnippets.querySelectorAll("snippet[snippet]").forEach((el) => {
            const value = el.getAttribute("snippet");
            el.dataset.oeType = "snippet";
            el.setAttribute("name", el.getAttribute("string"));
            const [module, key] = value.split(".");
            el.dataset.module = module;
            el.dataset.oeSnippetKey = key;
            if (el.hasAttribute("thumbnail")) {
                el.dataset.oeThumbnail = el.getAttribute("thumbnail");
            } else {
                el.dataset.oeThumbnail = "oe-thumbnail";
            }
            if (el.hasAttribute("group")) {
                el.dataset.oGroup = el.getAttribute("group");
            }
            if (el.hasAttribute("label")) {
                el.dataset.oLabel = el.getAttribute("label");
            }
            el.append(renderToElement(value, globalValues));
            el.firstElementChild.dataset.snippet = el.dataset.oeSnippetKey;
        });

        for (const category of builtinMMSnippets.querySelectorAll("snippets")) {
            const documentCategoryElement = this.snippetsDocument.getElementById(category.id);
            if (!documentCategoryElement) {
                this.snippetsDocument.body.append(category);
            } else {
                documentCategoryElement.append(...category.children);
            }
        }
        return this.snippetsDocument;
    }
}

registry
    .category("html_builder.snippetsModel")
    .add("mass_mailing.email_designer_snippets", MassMailingSnippetModel);
