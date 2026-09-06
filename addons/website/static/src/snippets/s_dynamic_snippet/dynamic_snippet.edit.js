import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rewrapDynamicSnippet } from "@website/js/content/wrap_dynamic_snippet";

class RewrapDynamicSnippetEdit extends Interaction {
    static selector = ".s_dynamic_snippet_content";
    setup() {
        // rewrap after a shared snippet has been reloaded
        this.observer = new MutationObserver(() => rewrapDynamicSnippet(this.el));
        this.observer.observe(this.el, { childList: true });
        this.registerCleanup(() => this.observer.disconnect());
    }
}

class RewrapDynamicSnippetPreview extends Interaction {
    static selector = ".o_snippet_preview_wrap .s_dynamic_snippet_content";
    start() {
        // in preview `rewrapDynamicSnippet` is not run automatically
        this.observer = new ResizeObserver(() => {
            const isSmall = this.el.closest(".o_snippet_preview_wrap").offsetWidth < 767;
            rewrapDynamicSnippet(this.el, isSmall);
        });
        this.observer.observe(this.el);
        this.registerCleanup(() => this.observer.disconnect());
    }
}

registry.category("public.interactions.edit").add("website.rewrap_dynamic_snippet", {
    Interaction: RewrapDynamicSnippetEdit,
});
registry.category("public.interactions.preview").add("website.rewrap_dynamic_snippet", {
    Interaction: RewrapDynamicSnippetPreview,
});
