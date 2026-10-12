/**
 * Scrolls a horizontally scrollable container to ensure a specific item is visible
 *
 * @param {HTMLElement} scrollEl - The scrollable container element
 * @param {string} querySelector - A CSS selector to find the target item inside the container
 * @param {Object} [options] - Optional configuration.
 * @param {'start' | 'auto'} [options.align='start'] - If 'start', aligns the item to the left edge.
 * @param {number} [options.edgePadding=50] - Extra space to keep between the item and the container's edge
 * @param {'auto' | 'smooth'} [options.scrollBehavior='smooth'] - Defines the scroll animation behavior
 * @param {number} [options.minRightGap] - In 'start' mode, skips scrolling if item’s right edge is within this distance from container’s right edge.
 **/
export function scrollItemIntoViewX(
    scrollEl,
    querySelector,
    { align = "start", edgePadding = 5, minRightGap = 100, scrollBehavior = "smooth" } = {}
) {
    if (!scrollEl || !querySelector) {
        return;
    }

    const itemEl = scrollEl.querySelector(querySelector);
    if (!itemEl) {
        return;
    }

    const containerRect = scrollEl.getBoundingClientRect();
    const itemRect = itemEl.getBoundingClientRect();

    if (align === "start") {
        const leftIsOutOfView = itemRect.left - edgePadding < containerRect.left;
        const rightGap = containerRect.right - itemRect.right;
        if (!leftIsOutOfView && rightGap >= minRightGap) {
            return;
        }

        const offset = itemRect.left - containerRect.left - edgePadding;
        scrollEl.scrollBy({ left: offset, behavior: scrollBehavior });
        return;
    }

    const leftDiff = itemRect.left - containerRect.left;
    const rightDiff = itemRect.right - containerRect.right;

    let offset = 0;
    if (leftDiff < edgePadding) {
        offset = leftDiff - edgePadding;
    } else if (rightDiff > -edgePadding) {
        offset = rightDiff + edgePadding;
    } else {
        return;
    }

    scrollEl.scrollBy({ left: offset, behavior: scrollBehavior });
}
