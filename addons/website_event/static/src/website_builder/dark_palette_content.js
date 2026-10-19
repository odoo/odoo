import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

registry
    .category("website.dark_palette_content_adaptations")
    .add("website_event.single_events", (rootEl) => {
        for (const contentEl of selectElements(
            rootEl,
            '[class*="s_event_event_single_"] .s_dynamic_snippet_content.o_cc5'
        )) {
            contentEl.classList.replace("o_cc5", "o_cc1");
        }
    });
