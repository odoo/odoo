// Definitely not the right location for this file !!!

/**
 * @param {HTMLElement} element
 */
export function onceAllImagesLoaded(element) {
    const imgEls = element.nodeName === "IMG" ? [element] : [...element.querySelectorAll("img")];
    const defs = imgEls.map((imgEl) => {
        if (imgEl.complete) {
            return; // Already loaded
        }
        return new Promise((resolve, reject) => {
            imgEl.addEventListener("load", resolve, { once: true });
            imgEl.addEventListener("error", reject, { once: true });
        });
    });
    return Promise.all(defs);
}
