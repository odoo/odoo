import { _t } from "@web/core/l10n/translation";

const ARIA_LABELS = {
    ".o_editor_banner.alert-danger": _t("Banner Danger"),
    ".o_editor_banner.alert-info": _t("Banner Info"),
    ".o_editor_banner.alert-success": _t("Banner Success"),
    ".o_editor_banner.alert-warning": _t("Banner Warning"),
};

function getAriaLabel(element) {
    for (const [selector, ariaLabel] of Object.entries(ARIA_LABELS)) {
        if (element.matches(selector)) {
            return ariaLabel;
        }
    }
}

/**
 * Replace the `o_editable` and `o_not_editable` on `banner` elements by
 * `o-contenteditable-true` and `o-content-editable-false`.
 * Add `o_editor_banner_content` to the content parent element.
 * Add accessibility editor-specific attributes (data-oe-role and
 * data-oe-aria-label).
 *
 * @param {HTMLElement} container
 */
export function migrate(container) {
    const bannerContainers = container.querySelectorAll(".o_editor_banner");
    for (const bannerContainer of bannerContainers) {
        bannerContainer.classList.remove("o_not_editable");
        bannerContainer.classList.add("o-contenteditable-false");
        bannerContainer.dataset.oeRole = "status";
        const icon = bannerContainer.querySelector(".o_editor_banner_icon");
        if (icon) {
            const ariaLabel = getAriaLabel(bannerContainer);
            if (ariaLabel) {
                icon.dataset.oeAriaLabel = ariaLabel;
            }
        }
        const bannerContent = bannerContainer.querySelector(".o_editor_banner_icon ~ div");
        if (bannerContent) {
            bannerContent.classList.remove("o_editable");
            bannerContent.classList.add("o_editor_banner_content");
            bannerContent.classList.add("o-contenteditable-true");
        }
    }
}
