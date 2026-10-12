import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { user } from "@web/core/user";
import { nbsp } from "@web/core/utils/strings";
import { children } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

async function getSnippetsRenderingContext(orm, context) {
    const companyData = await orm.call("res.company", "get_mailing_snippet_info", [
        user.defaultCompany.id,
    ]);
    const renderingContext = {
        ...context,
        user_id: {
            ...user,
            id: user.userId,
        },
        company_id: {
            ...user.defaultCompany,
            ...companyData,
        },
        now: DateTime.now(),
        nbsp,
    };

    return renderingContext;
}

registry
    .category("html_builder.snippetsPreprocessor")
    .add("email_designer_snippets", async (snippetsName, snippetsDoc, options) => {
        if (snippetsName !== "mass_mailing.email_designer_snippets") {
            return;
        }
        const { orm, context } = options;

        const renderingContext = await getSnippetsRenderingContext(orm, context);
        const snippets = renderToFragment(snippetsName, renderingContext);

        // Modify fragment's categories and snippets' attributes to match expected document format
        snippets.querySelectorAll("group[snippet-group]").forEach((el) => {
            el.dataset.oSnippetGroup = el.getAttribute("snippet-group");
            if (el.hasAttribute("thumbnail")) {
                el.dataset.oeThumbnail = el.getAttribute("thumbnail");
            }
            el.append(renderToElement("mass_mailing.s_snippet_group"));
        });
        snippets.querySelectorAll("snippet[snippet]").forEach((el) => {
            const snippetTemplateId = el.getAttribute("snippet");
            el.dataset.oeType = "snippet";
            const [module, key] = snippetTemplateId.split(".");
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
            el.append(renderToElement(snippetTemplateId, renderingContext));
            el.firstElementChild.dataset.snippet = el.dataset.oeSnippetKey;
            if (!el.firstElementChild.dataset.name) {
                el.firstElementChild.dataset.name = el.getAttribute("name");
            }
        });

        // Insert MM categories into snippets document
        for (const category of snippets.querySelectorAll("snippets")) {
            const documentCategoryElement = snippetsDoc.getElementById(category.id);
            if (!documentCategoryElement) {
                snippetsDoc.body.append(category);
            } else {
                documentCategoryElement.append(children(category));
            }
        }
    });
