import { Component, signal, t, usePlugin, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { HotkeyPlugin } from "@web/core/hotkeys/hotkey_plugin";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { findLowContrastElements } from "./contrast";

const WARNING_CLASS = "o_website_theme_colors_preview_contrast_warning";
const LOW_CONTRAST_CLASS = "o_website_theme_colors_preview_low_contrast";
const LABEL_CLASS = "o_website_theme_colors_preview_label";

export class ThemeColorsPreviewDialog extends Component {
    static template = "website.ThemeColorsPreviewDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        onIframeLoad: t.function(),
    });
    hasLowContrast = signal(false);

    setup() {
        this.hotkey = usePlugin(HotkeyPlugin);
        this.tooltip = usePopover(Tooltip, { role: "tooltip" });
    }

    onIframeLoad(ev) {
        this.hotkey.registerIframe(ev.target);
        const previewDocument = ev.target.contentDocument;
        this.props.onIframeLoad(previewDocument);
        this.markLowContrastElements(previewDocument.body);
        // Theme color changes reload the stylesheets of the preview.
        previewDocument.addEventListener("bundles_reloaded", () => {
            this.tooltip.close();
            this.markLowContrastElements(previewDocument.body);
        });
    }

    /**
     * Mark the text of `rootEl` that is not contrasted enough with a warning icon.
     *
     * @param {HTMLElement} rootEl
     */
    markLowContrastElements(rootEl) {
        rootEl.querySelectorAll(`.${WARNING_CLASS}`).forEach((el) => el.remove());
        rootEl
            .querySelectorAll(`.${LOW_CONTRAST_CLASS}`)
            .forEach((el) => el.classList.remove(LOW_CONTRAST_CLASS));
        for (const labelEl of rootEl.querySelectorAll(`.${LABEL_CLASS}`)) {
            for (const lowContrast of findLowContrastElements(labelEl.parentElement)) {
                this.addWarning(lowContrast, labelEl.textContent.trim());
            }
        }
        this.hasLowContrast.set(Boolean(rootEl.querySelector(`.${WARNING_CLASS}`)));
    }

    addWarning({ el, ratio, threshold }, group) {
        const doc = el.ownerDocument;
        const tooltip = _t("Contrast: %(actualRatio)s (minimum %(thresholdRatio)s)", {
            // Rounding up could display a failing ratio as the minimum.
            actualRatio: `${Math.floor(ratio * 100) / 100}:1`,
            thresholdRatio: `${threshold}:1`,
        });
        const warningEl = doc.createElement("button");
        warningEl.type = "button";
        warningEl.className = WARNING_CLASS;
        warningEl.setAttribute(
            "aria-label",
            _t("%(group)s, %(text)s, Low contrast", { group, text: el.textContent.trim() })
        );
        warningEl.setAttribute("aria-description", tooltip);
        const openTooltip = () => this.tooltip.open(warningEl, { tooltip });
        warningEl.addEventListener("mouseenter", openTooltip);
        warningEl.addEventListener("focus", openTooltip);
        warningEl.addEventListener("mouseleave", () => this.tooltip.close());
        warningEl.addEventListener("focusout", () => this.tooltip.close());
        const iconEl = doc.createElement("span");
        iconEl.className = "oi";
        iconEl.dataset.icon = "priority_high";
        iconEl.ariaHidden = "true";
        warningEl.append(iconEl);
        el.classList.add(LOW_CONTRAST_CLASS);
        el.append(warningEl);
    }
}
