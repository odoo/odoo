/**
 * Get the closest horizontally scrollable for a given element.
 *
 * @param {HTMLElement} el
 * @returns {HTMLElement | null}
 */
export function closestScrollableX(el) {
    if (!el) {
        return null;
    }
    if (el.scrollWidth > el.clientWidth && el.clientWidth > 0) {
        const overflow = getComputedStyle(el).getPropertyValue("overflow-x");
        if (/\bauto\b|\bscroll\b/.test(overflow)) {
            return el;
        }
    }
    return closestScrollableX(el.parentElement);
}

/**
 * Get the closest vertically scrollable for a given element.
 *
 * @param {HTMLElement} el
 * @returns {HTMLElement | null}
 */
export function closestScrollableY(el) {
    if (!el) {
        return null;
    }
    if (el.scrollHeight > el.clientHeight && el.clientHeight > 0) {
        const overflow = getComputedStyle(el).getPropertyValue("overflow-y");
        if (/\bauto\b|\bscroll\b/.test(overflow)) {
            return el;
        }
    }
    return closestScrollableY(el.parentElement);
}

/**
 * Ensures that `element` will be visible in its `scrollable`.
 *
 * @param {HTMLElement} element
 * @param {object} options
 * @param {HTMLElement} [options.scrollable] a scrollable area
 * @param {boolean} [options.isAnchor] states if the scroll is to an anchor
 * @param {string} [options.behavior] "smooth", "instant", "auto" <=> undefined
 *        @url https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollTo#behavior
 * @param {number} [options.offset] applies a vertical offset
 */
export function scrollTo(element, options = {}) {
    const { behavior = "auto", isAnchor = false, offset = 0 } = options;
    const scrollable = closestScrollableY(options.scrollable || element.parentElement);
    if (!scrollable) {
        return;
    }

    const scrollBottom = scrollable.getBoundingClientRect().bottom;
    const scrollTop = scrollable.getBoundingClientRect().top;
    const elementBottom = element.getBoundingClientRect().bottom;
    const elementTop = element.getBoundingClientRect().top;

    const scrollPromises = [];

    if (elementBottom > scrollBottom && !isAnchor) {
        // The scroll place the element at the bottom border of the scrollable
        scrollPromises.push(
            new Promise((resolve) => {
                scrollable.addEventListener("scrollend", () => resolve(), { once: true });
            })
        );

        scrollable.scrollTo({
            top:
                scrollable.scrollTop +
                elementTop -
                scrollBottom +
                Math.ceil(element.getBoundingClientRect().height) +
                offset,
            behavior,
        });
    }  else if (elementTop < scrollTop || isAnchor) {
        // The scroll place the element at the top of the scrollable
        scrollPromises.push(
            new Promise((resolve) => {
                scrollable.addEventListener("scrollend", () => resolve(), { once: true });
            })
        );

        scrollable.scrollTo({
            top: scrollable.scrollTop - scrollTop + elementTop + offset,
            behavior,
        });

        if (options.isAnchor) {
            // If the scrollable is within a scrollable, another scroll should be done
            const parentScrollable = closestScrollableY(scrollable.parentElement);
            if (parentScrollable) {
                scrollPromises.push(
                    scrollTo(scrollable, {
                        behavior,
                        isAnchor: true,
                        scrollable: parentScrollable,
                    })
                );
            }
        }
    }

    return Promise.all(scrollPromises);
}
