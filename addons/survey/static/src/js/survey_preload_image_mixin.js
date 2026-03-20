/**
 * Load the target section background and render it when loaded.
 *
 * This method is used to pre-load the image during the questions transitions (fade out) in order
 * to be sure the image is fully loaded when setting it as background of the next question and
 * finally display it (fade in)
 *
 * This idea is to wait until new background is loaded before changing the background
 * (to avoid flickering or loading latency)
 *
 * @param {string} imageUrl
 * @private
 */
export async function preloadBackground(imageUrl) {
    let resolvePreload;

    // We have to manually create a promise here because the "onload" API does not provide one.
    const preloadPromise = new Promise(function (resolve, reject) {
        resolvePreload = resolve;
    });
    const background = new Image();
    background.addEventListener("load", () => resolvePreload(imageUrl), { once: true });
    background.src = imageUrl;

    return preloadPromise;
}
