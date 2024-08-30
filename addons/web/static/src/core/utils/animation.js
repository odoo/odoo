/**
 * Clear any ongoing animations
 */
function clearAnimation(element) {
    element.style.transition = "none";
    element.style.opacity = getComputedStyle(element).opacity; // Get the current opacity
    element.offsetHeight; // Trigger a reflow, flushing the CSS changes
}
/**
 *
 * @param {Element} el
 * @param {Integer} duration it must be in ms
 *
 */
export function fadeIn(el, duration) {
    clearAnimation(el);

    // Now set up the fade in transition
    el.classList.remove("d-none");
    el.style.transition = `opacity ${duration}ms ease`;
    el.style.opacity = 1;

    // Remove the transition style after the transition ends
    el.addEventListener("transitionend", function (ev) {
        ev.currentTarget.style.transition = "";
    });
}
/**
 *
 * @param {Element} el
 * @param {Integer} duration it must be in ms
 *
 */

export function fadeOut(el, duration) {
    clearAnimation(el);

    // Now set up the fade out transition
    el.style.transition = `opacity ${duration}ms ease`;
    el.style.opacity = 0;

    // Add an event listener to remove the element from the DOM after the transition ends
    el.addEventListener("transitionend", function (ev) {
        ev.currentTarget.classList.add("d-none");
    });
}
