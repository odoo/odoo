import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";
import { setElementContent } from "@web/core/utils/html";

class SharedSnippetContent extends Interaction {
    static selector = "[data-oe-shared-snippet]";

    async willStart() {
        const sharedSnippetName = this.el.dataset.oeSharedSnippet;
        const sharedSnippetArgs = Object.fromEntries(
            this.el
                .getAttributeNames()
                .filter((name) => name.startsWith("data-arg-"))
                .map((name) => [
                    name.slice("data-arg-".length),
                    JSON.parse(this.el.getAttribute(name)),
                ])
        );
        const fieldEl = this.el.closest("[data-oe-field]");
        const mainObject =
            !fieldEl || ["arch", "arch_db"].includes(fieldEl.dataset.oeField)
                ? this.services.website_page.mainObject
                : { model: fieldEl.dataset.oeModel, id: parseInt(fieldEl.dataset.oeId) };
        this.content = markup(
            await this.services.orm.silent.call(
                "ir.ui.view",
                "render_shared_snippet",
                [sharedSnippetName, sharedSnippetArgs, mainObject.model, mainObject.id],
                {
                    context: {
                        dynamic_filter_snippet_with_sample: true,
                        lang: this.services.website_page.context.lang,
                        website_id: this.services.website_page.context.website_id,
                    },
                }
            )
        );
    }

    start() {
        setElementContent(this.el, this.content);
        this.services["public.interactions"].startInteractions(this.el);
    }
}

registry.category("public.interactions.edit").add("website.shared_snippet_content", {
    Interaction: SharedSnippetContent,
});
