/**
 * The set of blocks the "Animation" theme option animates is defined by a CSS
 * selector only (see "$o-wanim-default-selector" in website.scss), which no
 * computed style can be asked about: hence this class, added at runtime from
 * the selector the CSS exports, and never saved.
 */
export const DEFAULT_ANIMATION_CLASS = "o_animate_default";

/**
 * @returns {string} empty if the "Animation" theme option is turned off
 */
export function getDefaultAnimationSelector(doc) {
    return doc.defaultView
        .getComputedStyle(doc.documentElement)
        .getPropertyValue("--o-wanim-default-selector")
        .trim();
}

export function applyDefaultAnimationClass(rootEl) {
    const selector = getDefaultAnimationSelector(rootEl.ownerDocument);
    if (!selector) {
        return;
    }
    const els = [...rootEl.querySelectorAll(selector)];
    // The root itself when called on freshly inserted content.
    if (rootEl.matches(selector)) {
        els.push(rootEl);
    }
    els.forEach((el) => el.classList.add(DEFAULT_ANIMATION_CLASS));
}
