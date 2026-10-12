export const dynamicSVGSelector = "img[src^='/html_editor/shape/'], img[src^='/web_editor/shape/']";

export function applyFunDependOnSelectorAndExclude(fn, rootEl, selectorParams) {
    const editingEls = getEditingEls(rootEl, selectorParams);
    if (!editingEls.length) {
        return false;
    }
    return Promise.all(editingEls.map((el) => fn(el)));
}

export function getEditingEls(rootEl, { selector, exclude, applyTo }) {
    const closestSelector = rootEl.closest(selector);
    let editingEls = closestSelector ? [closestSelector] : [...rootEl.querySelectorAll(selector)];
    if (exclude) {
        editingEls = editingEls.filter((selectorEl) => !selectorEl.matches(exclude));
    }
    if (!applyTo) {
        return editingEls;
    }
    const targetEls = [];
    for (const editingEl of editingEls) {
        const applyToEls = applyTo ? editingEl.querySelectorAll(applyTo) : [editingEl];
        targetEls.push(...applyToEls);
    }
    return targetEls;
}

export const setHrefUrl = (targetEl, url) => {
    if (!url) {
        // If no URL is provided, remove the href attribute to avoid treating
        // elements (e.g. images) as links and to clean up empty links.
        targetEl.removeAttribute("href");
        return;
    }
    if (!url.startsWith("/") && !url.startsWith("#") && !/^([a-zA-Z]*.):.+$/gm.test(url)) {
        // We permit every protocol (http:, https:, ftp:, mailto:,...).
        // If none is explicitly specified, we assume it is a http.
        url = "http://" + url;
    }
    targetEl.setAttribute("href", url);
};
