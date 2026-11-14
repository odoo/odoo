import { Component, t, useProps } from "@odoo/owl";
import { findLowContrastElements } from "./contrast";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

const WARNING_CLASS = "o_theme_colors_preview_contrast_warning";
const LOW_CONTRAST_CLASS = "o_theme_colors_preview_low_contrast";

/**
 * Mark the text of `rootEl` that is not contrasted enough with a warning icon.
 *
 * @param {HTMLElement} rootEl
 */
export function markLowContrastElements(rootEl) {
    rootEl.querySelectorAll(`.${WARNING_CLASS}`).forEach((el) => el.remove());
    rootEl
        .querySelectorAll(`.${LOW_CONTRAST_CLASS}`)
        .forEach((el) => el.classList.remove(LOW_CONTRAST_CLASS));
    const message = _t(
        "This element with low contrast is difficult for many users to read. You can either change the background color or the element color."
    );
    for (const { el } of findLowContrastElements(rootEl)) {
        const iconEl = rootEl.ownerDocument.createElement("i");
        iconEl.className = `oi ${WARNING_CLASS}`;
        iconEl.dataset.icon = "warning";
        iconEl.setAttribute("role", "img");
        iconEl.setAttribute("aria-label", message);
        iconEl.title = message;
        el.classList.add(LOW_CONTRAST_CLASS);
        el.append(iconEl);
    }
}

export class ThemeColorsPreviewDialog extends Component {
    static template = "website.ThemeColorsPreviewDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        onIframeLoad: t.function(),
    });

    onIframeLoad(ev) {
        this.previewDocument = ev.target.contentDocument;
        this.props.onIframeLoad(this.previewDocument);
        markLowContrastElements(this.previewDocument.body);
        // Theme color changes reload the stylesheets of the preview.
        this.previewDocument.addEventListener("bundles_reloaded", () =>
            markLowContrastElements(this.previewDocument.body)
        );
    }
}
