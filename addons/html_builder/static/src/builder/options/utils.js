export function applyFunDependOnSelectorAndExclude(fn, rootEl, selector, exclude = "") {
    const closestSelector = rootEl.closest(selector);
    const selectorEls = closestSelector
        ? [closestSelector]
        : [...rootEl.querySelectorAll(selector)];
    const editingEls = selectorEls.filter((selectorEl) => !selectorEl.matches(exclude));
    for (const editingEl of editingEls) {
        fn(editingEl);
    }
}
