import { debounce } from "@web/core/utils/timing";

// Constants for class names and data attributes
export const MASONRY = {
    CLASSES: {
        MODE: "o_masonry_mode",
        FIXED_COLUMNS: "s_nb_column_fixed",
        COLUMN: "o_masonry_col",
        ITEM: "w-100",
        NOT_SELECTABLE: "o_snippet_not_selectable",
    },
    DATA_ATTRS: {
        DESKTOP_COLUMNS: "data-columns",
        MOBILE_COLUMNS: "data-mobile-columns",
        ITEM_INDEX: "data-index",
    },
    DEFAULTS: {
        DESKTOP_COLUMNS: 3,
        MOBILE_COLUMNS: 1,
    },
};

/**
 * Gets the number of columns for desktop and mobile based on container's
 * column attribute (between 1 and 12).
 *
 * @private
 * @param {Element} containerEl - The container element
 * @returns {Object} Object containing desktop and mobile column counts
 */
function _getColumnConfiguration(containerEl) {
    const desktopColumnCount =
        parseInt(containerEl.parentElement.getAttribute(MASONRY.DATA_ATTRS.DESKTOP_COLUMNS)) ||
        MASONRY.DEFAULTS.DESKTOP_COLUMNS;
    const mobileColumnCount =
        parseInt(containerEl.parentElement.getAttribute(MASONRY.DATA_ATTRS.MOBILE_COLUMNS)) ||
        MASONRY.DEFAULTS.MOBILE_COLUMNS;

    return {
        desktop: Math.min(Math.max(desktopColumnCount, 1), 12),
        mobile: Math.min(Math.max(mobileColumnCount, 1), 12),
    };
}

/**
 * Creates masonry column elements based on the configuration.
 *
 * @private
 * @param {number} desktopColumnCount - Number of columns for desktop
 * @param {number} mobileColumnCount - Number of columns for mobile
 * @returns {Element[]} Array of column elements
 */
function _createColumnElements(desktopColumnCount, mobileColumnCount) {
    const columnEls = [];
    const desktopColSpan = Math.floor(12 / desktopColumnCount);
    const mobileColSpan = Math.floor(12 / mobileColumnCount);

    for (let i = 0; i < desktopColumnCount; i++) {
        const columnEl = document.createElement("div");
        columnEl.classList.add(
            MASONRY.CLASSES.COLUMN,
            MASONRY.CLASSES.NOT_SELECTABLE,
            `col-${mobileColSpan}`,
            `col-lg-${desktopColSpan}`
        );
        columnEls.push(columnEl);
    }

    return columnEls;
}

/**
 * Finds the shortest column in the masonry layout.
 *
 * @private
 * @param {Element[]} columnEls - Array of column elements
 * @returns {Element} The shortest column element
 */
function _getShortestColumn(columnEls) {
    return columnEls.reduce((shortestEl, currentEl) => {
        const currentHeight = currentEl.lastElementChild
            ? currentEl.lastElementChild.getBoundingClientRect().bottom
            : currentEl.getBoundingClientRect().top;
        const shortestHeight = shortestEl.lastElementChild
            ? shortestEl.lastElementChild.getBoundingClientRect().bottom
            : shortestEl.getBoundingClientRect().top;

        return currentHeight < shortestHeight ? currentEl : shortestEl;
    }, columnEls[0]);
}

/**
 * Retrieves and sorts the original elements from the row based on the defined
 * data index attribute.
 * It also considers the possibility of elements being wrapped in a
 * link (anchor) tag.
 *
 * @param {Element} rowEl - The row element containing child elements with data
 *                          index attributes.
 * @returns {Element[]} An array of child elements or their wrappers sorted by
 *                      the specified data index attribute.
 */
export function _getOriginalElements(rowEl) {
    if (!rowEl || !rowEl.children) {
        return [];
    }

    const hasIndex = (el) => el?.hasAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX);
    const getIndex = (el) => {
        if (el.hasAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX)) {
            return Number(el.getAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX));
        }

        // original el possibly wrapped in an anchor tag
        const firstChildEl = el.firstChild;
        if (firstChildEl?.hasAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX)) {
            return Number(firstChildEl.getAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX));
        }

        return 0;
    };

    return Array.from(rowEl.children)
        .filter((el) => hasIndex(el) || hasIndex(el.firstChild))
        .sort((firstEl, secondEl) => getIndex(firstEl) - getIndex(secondEl));
}

/**
 * Creates the masonry layout by organizing elements one by one in the
 * shortest column.
 *
 * @param {Element} rowEl - The row element containing the items to organize
 * @param {number} desktopColumnCount - Number of columns for desktop view
 * @param {number} mobileColumnCount - Number of columns for mobile view
 * @returns {Promise} Resolves when all images are loaded and placed
 */
async function _createMasonryLayout(rowEl, desktopColumnCount, mobileColumnCount) {
    if (!rowEl) {
        return Promise.resolve();
    }

    const originalEls = _getOriginalElements(rowEl);
    if (!originalEls.length) {
        return Promise.resolve();
    }

    // Clear row and create masonry columns
    rowEl.innerHTML = "";
    const columnEls = _createColumnElements(desktopColumnCount, mobileColumnCount);
    columnEls.forEach((colEl) => rowEl.appendChild(colEl));
    rowEl.classList.add(MASONRY.CLASSES.MODE, MASONRY.CLASSES.FIXED_COLUMNS);

    // Distribute items across the columns
    // eslint-disable-next-line no-async-promise-executor
    return new Promise(async (resolve) => {
        const originallyHiddenEls = [];
        for (const el of originalEls) {
            el.classList.add(MASONRY.CLASSES.ITEM);
            const shortestColumnEl = _getShortestColumn(columnEls);
            const clonedEl = el.cloneNode(true);
            if (clonedEl.classList.contains("d-none")) {
                clonedEl.classList.remove("d-none");
                clonedEl.classList.add("opacity-0");
                originallyHiddenEls.push(clonedEl);
            }
            shortestColumnEl.appendChild(clonedEl);

            // wait for images to load to get correct column height
            // TODO: move onceAllImagesLoaded in web_editor and to use it here
            const imageEls = shortestColumnEl.querySelectorAll("img");
            await Promise.all(
                Array.from(imageEls).map((imgEl) => {
                    return new Promise((resolve) => {
                        if (imgEl.complete) {
                            resolve();
                        } else {
                            imgEl.onload = () => resolve();
                        }
                    });
                })
            );
        }
        for (const el of originallyHiddenEls) {
            el.classList.add("d-none");
            el.classList.remove("opacity-0");
        }
        resolve();
    });
}

/**
 * Toggles the masonry layout mode for the given container element.
 * Ensures the container has a `.row` element, which acts as the parent for
 * masonry columns.
 *
 * @public
 * @param {Element} containerEl - Element with the class "container", consisting
 *                                of a child with the class "row" that holds all
 *                                the masonry items.
 * @returns {Promise} Resolves when all images are loaded and placed
 */
export async function toggleMasonryMode(containerEl) {
    if (!containerEl) {
        return Promise.resolve();
    }

    let rowEl = containerEl.querySelector(":scope > .row");
    const outOfRowEls = [...containerEl.children].filter((el) => !el.classList.contains("row"));

    // Create row if needed
    if (!rowEl) {
        rowEl = document.createElement("div");
        rowEl.classList.add("row");
        [...containerEl.children].forEach((childEl) => rowEl.appendChild(childEl));
        containerEl.appendChild(rowEl);
    }

    // Add out-of-row elements to row
    outOfRowEls.forEach((el) => rowEl.appendChild(el));

    const { desktop: desktopColumnCount, mobile: mobileColumnCount } =
        _getColumnConfiguration(containerEl);
    await _createMasonryLayout(rowEl, desktopColumnCount, mobileColumnCount);
}

/**
 * Clears the masonry layout
 *
 * @public
 * @param {Element} rowEl - The row element containing the masonry layout
 */
export function clearMasonryLayout(rowEl) {
    if (!rowEl) {
        return;
    }

    rowEl.classList.remove(MASONRY.CLASSES.MODE, MASONRY.CLASSES.FIXED_COLUMNS);

    const originalEls = [];
    rowEl.querySelectorAll(`.${MASONRY.CLASSES.COLUMN}`).forEach((colEl) => {
        originalEls.push(...colEl.children);
        colEl.remove();
    });

    originalEls.forEach((el) => rowEl.appendChild(el));
}

/**
 * Updates the column configuration for a container
 *
 * @public
 * @param {Element} containerEl - The container element
 * @param {Object} config - Configuration object
 * @param {number} [config.desktopColumnCount] - Number of columns for desktop view
 * @param {number} [config.mobileColumnCount] - Number of columns for mobile view
 */
export function updateMasonryConfig(containerEl, { desktopColumnCount, mobileColumnCount } = {}) {
    if (desktopColumnCount !== undefined) {
        containerEl.setAttribute(MASONRY.DATA_ATTRS.DESKTOP_COLUMNS, desktopColumnCount);
    }
    if (mobileColumnCount !== undefined) {
        containerEl.setAttribute(MASONRY.DATA_ATTRS.MOBILE_COLUMNS, mobileColumnCount);
    }

    // Reapply masonry layout if it's already active
    const rowEl = containerEl.querySelector(":scope > .row");
    if (rowEl && rowEl.classList.contains(MASONRY.CLASSES.MODE)) {
        toggleMasonryMode(containerEl);
    }
}

/**
 * Creates a resize observer for automatically updating masonry layout when the
 * screen size changes.
 *
 * @public
 * @param {Element} sectionEl - The section element to observe
 * @param {number} [debounceTime=100] - Debounce time in milliseconds
 * @returns {ResizeObserver} The resize observer instance
 */
export function observeMasonryContainerResize(sectionEl, debounceTime = 100) {
    if (!sectionEl) {
        return null;
    }

    const masonryRowEl = sectionEl.querySelector(`.${MASONRY.CLASSES.MODE}`);
    if (!masonryRowEl) {
        return null;
    }

    const resizeObserver = new ResizeObserver(
        debounce(toggleMasonryMode.bind(this, sectionEl.querySelector(".container")), debounceTime)
    );
    resizeObserver.observe(masonryRowEl);
    return resizeObserver;
}
