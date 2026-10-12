import { Plugin, types as t, useConfig, useListener } from "@odoo/owl";

export const TEXT_TRUNCATE_TOOLTIP_SELECTOR = "[data-text-truncate-tooltip]";

/**
 * Adds a tooltip containing the full text of any truncated element marked with
 * `data-text-truncate-tooltip`. If the element already belongs to a tooltip,
 * its full text is prepended to the existing tooltip content.
 */
export class TextTruncateTooltipPlugin extends Plugin {
    setup() {
        const rootRef = useConfig("rootRef", t.function());

        const onTooltipTrigger = (ev) => {
            const targetEl = ev.target;
            let textEl;
            const textTooltipEl = targetEl.closest?.(TEXT_TRUNCATE_TOOLTIP_SELECTOR);
            if (textTooltipEl) {
                textEl = textTooltipEl;
            } else {
                // Handle hovering an element next to the truncated text.
                // Example: the BuilderRow question icon.
                textEl = targetEl
                    .closest?.("[data-tooltip]")
                    ?.querySelector(TEXT_TRUNCATE_TOOLTIP_SELECTOR);
            }
            if (textEl && textEl.dataset.textTruncateTooltipChecked === undefined) {
                const tooltipEl = textEl.closest("[data-tooltip]") || textEl;
                textEl.dataset.textTruncateTooltipChecked = "true";
                if (textEl.offsetWidth < textEl.scrollWidth) {
                    const baseTooltip = tooltipEl.dataset.tooltip || "";
                    const text = textEl.textContent.trim();
                    tooltipEl.dataset.tooltip = baseTooltip
                        ? `${text}\u00A0: ${baseTooltip}`
                        : text;
                }
            }
        };

        useListener(rootRef, "pointerover", onTooltipTrigger);
    }
}
