import { config } from "@web/core/transition";

export function animateExpand(elementEl, expanded = true) {
    if (
        config.disabled ||
        elementEl.ownerDocument.defaultView.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
        return;
    }
    const style = getComputedStyle(elementEl);
    return elementEl.animate(
        {
            height: ["0px", style.height],
            minHeight: ["0px", "0px"],
            paddingTop: ["0px", style.paddingTop],
            paddingBottom: ["0px", style.paddingBottom],
            marginTop: ["0px", style.marginTop],
            marginBottom: ["0px", style.marginBottom],
            overflow: ["hidden", "hidden"],
        },
        {
            duration: 150,
            easing: "ease",
            direction: expanded ? "normal" : "reverse",
            fill: expanded ? "auto" : "forwards",
        }
    );
}
