export function applyFunDependOnSelectorAndExclude(fn, rootEl, { selector, exclude, applyTo }) {
    const closestSelector = rootEl.closest(selector);
    let editingEls = closestSelector ? [closestSelector] : [...rootEl.querySelectorAll(selector)];
    if (exclude) {
        editingEls = editingEls.filter((selectorEl) => !selectorEl.matches(exclude));
    }
    for (const editingEl of editingEls) {
        const targetEls = applyTo ? editingEl.querySelectorAll(applyTo) : [editingEl];
        for (const targetEl of targetEls) {
            fn(targetEl);
        }
    }
}

export async function applyAsyncFunDependOnSelectorAndExclude(
    fn,
    rootEl,
    { selector, exclude, applyTo }
) {
    const closestSelector = rootEl.closest(selector);
    let editingEls = closestSelector ? [closestSelector] : [...rootEl.querySelectorAll(selector)];
    if (exclude) {
        editingEls = editingEls.filter((selectorEl) => !selectorEl.matches(exclude));
    }
    const proms = [];
    for (const editingEl of editingEls) {
        const targetEls = applyTo ? editingEl.querySelectorAll(applyTo) : [editingEl];
        for (const targetEl of targetEls) {
            proms.push(fn(targetEl));
        }
    }
    await Promise.all(proms);
}
