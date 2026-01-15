import { TextHighlight } from "@website/interactions/text_highlights";
import { registry } from "@web/core/registry";

const TextHighlightPreview = (I) =>
    class extends I {
        static selector = ".o_snippet_preview_wrap";
        static selectorHas = ".o_text_highlight";
    };

registry.category("public.interactions.preview").add("website.text_highlight", {
    Interaction: TextHighlight,
    mixin: TextHighlightPreview,
});
