export function applyFunDependOnSelectorAndExclude(fn, rootEl, selector, exclude) {
    const closestSelector = rootEl.closest(selector);
    let editingEls = closestSelector ? [closestSelector] : [...rootEl.querySelectorAll(selector)];
    if (exclude) {
        editingEls = editingEls.filter((selectorEl) => !selectorEl.matches(exclude));
    }
    for (const editingEl of editingEls) {
        fn(editingEl);
    }
}
