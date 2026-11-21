import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { findLowContrastElements } from "./contrast";

const WARNING_CLASS = "o_website_theme_colors_preview_contrast_warning";
const LOW_CONTRAST_CLASS = "o_website_theme_colors_preview_low_contrast";

class ContrastWarningPopover extends Component {
    static template = "website.ContrastWarningPopover";
    props = useProps({
        close: t.function(),
        ratio: t.number(),
        threshold: t.number(),
    });

    get contrastText() {
        return _t("Contrast: %(ratio)s:1 (minimum %(threshold)s:1)", {
            // Rounding up could display a failing ratio as the minimum.
            ratio: Math.floor(this.props.ratio * 100) / 100,
            threshold: this.props.threshold,
        });
    }
}

export class ThemeColorsPreviewDialog extends Component {
    static template = "website.ThemeColorsPreviewDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        onIframeLoad: t.function(),
    });

    setup() {
        this.popover = usePopover(ContrastWarningPopover, {
            onClose: () => this.openedWarningEl?.removeAttribute("aria-expanded"),
        });
    }

    onIframeLoad(ev) {
        const previewDocument = ev.target.contentDocument;
        this.props.onIframeLoad(previewDocument);
        this.markLowContrastElements(previewDocument.body);
        // Theme color changes reload the stylesheets of the preview.
        previewDocument.addEventListener("bundles_reloaded", () => {
            this.popover.close();
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
        for (const { el, ...contrast } of findLowContrastElements(rootEl)) {
            const buttonEl = rootEl.ownerDocument.createElement("button");
            buttonEl.type = "button";
            buttonEl.className = `oi ${WARNING_CLASS}`;
            buttonEl.dataset.icon = "priority_high";
            buttonEl.setAttribute("aria-label", _t("Low contrast"));
            buttonEl.title = _t("Click to see details");
            buttonEl.addEventListener("click", (ev) => this.openWarningPopover(ev, contrast));
            el.classList.add(LOW_CONTRAST_CLASS);
            el.append(buttonEl);
        }
    }

    /**
     * @param {Event} ev
     * @param {{ ratio: number, threshold: number }} contrast
     */
    openWarningPopover(ev, contrast) {
        ev.preventDefault();
        this.popover.open(ev.currentTarget, contrast);
        this.openedWarningEl = ev.currentTarget;
        this.openedWarningEl.setAttribute("aria-expanded", "true");
    }
}
