import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { patch } from "@web/core/utils/patch";
import { HighlightAnimatedText } from "./highlight_animated_text";

patch(InvisibleElementsPanel, {
    template: "website.InvisibleElementsPanel",
    components: { ...InvisibleElementsPanel.components, HighlightAnimatedText },
});
