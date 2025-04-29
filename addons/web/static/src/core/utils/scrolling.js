export function isScrollableX(el) {
    if (el.scrollWidth > el.clientWidth && el.clientWidth > 0) {
        return couldBeScrollableX(el);
    }
    return false;
}

export function couldBeScrollableX(el) {
    if (el) {
        const overflow = getComputedStyle(el).getPropertyValue("overflow-x");
        if (/\bauto\b|\bscroll\b/.test(overflow)) {
            return true;
        }
    }
    return false;
}

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
    if (isScrollableX(el)) {
        return el;
    }
    return closestScrollableX(el.parentElement);
}

export function isScrollableY(el) {
    if (el && el.scrollHeight > el.clientHeight && el.clientHeight > 0) {
        return couldBeScrollableY(el);
    }
    return false;
}

export function couldBeScrollableY(el) {
    if (el) {
        const overflow = getComputedStyle(el).getPropertyValue("overflow-y");
        if (/\bauto\b|\bscroll\b/.test(overflow)) {
            return true;
        }
    }
    return false;
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
    if (isScrollableY(el)) {
        return el;
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
    } else if (elementTop < scrollTop || isAnchor) {
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

export function compensateScrollbar(
    el,
    add = true,
    isScrollElement = true,
    cssProperty = "padding-right"
) {
    if (!el) {
        return;
    }
    // Compensate scrollbar
    const scrollableEl = isScrollElement ? el : closestScrollableY(el.parentElement);
    if (!scrollableEl) {
        return;
    }
    const isRTL = scrollableEl.classList.contains(".o_rtl");
    if (isRTL) {
        cssProperty = cssProperty.replace("right", "left");
    }
    el.style.removeProperty(cssProperty);
    if (!add) {
        return;
    }
    const style = window.getComputedStyle(el);
    // Round up to the nearest integer to be as close as possible to
    // the correct value in case of browser zoom.
    const borderLeftWidth = Math.ceil(parseFloat(style.borderLeftWidth.replace("px", "")));
    const borderRightWidth = Math.ceil(parseFloat(style.borderRightWidth.replace("px", "")));
    const bordersWidth = borderLeftWidth + borderRightWidth;
    const newValue =
        parseInt(style[cssProperty]) +
        scrollableEl.offsetWidth -
        scrollableEl.clientWidth -
        bordersWidth;
    el.style.setProperty(cssProperty, `${newValue}px`, "important");
}

export function getScrollingElement(document = window.document) {
    const baseScrollingElement = document.scrollingElement;
    if (isScrollableY(baseScrollingElement)) {
        return baseScrollingElement;
    }
    const bodyHeight = window.getComputedStyle(document.body).height;
    for (const el of document.body.children) {
        // Search for a body child which is at least as tall as the body
        // and which has the ability to scroll if enough content in it. If
        // found, suppose this is the top scrolling element.
        if (bodyHeight - el.scrollHeight > 1.5) {
            continue;
        }
        if (isScrollableY(el)) {
            return el;
        }
    }
    return baseScrollingElement;
}

export function getScrollingTarget(scrollingElement = window.document) {
    const document = scrollingElement.ownerDocument;
    return scrollingElement === document.scrollingElement ? document.defaultView : scrollingElement;
}
