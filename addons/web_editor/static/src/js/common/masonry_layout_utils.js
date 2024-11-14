import { debounce } from "@web/core/utils/timing";

// Constants for class names and data attributes
export const MASONRY = {
    CLASSES: {
        MODE: "o_masonry",
        CONTAINER_CLASSES: ["o_container_small", "container", "container-fluid"],
        ROW: "o_masonry_mode",
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
        parseInt(containerEl.getAttribute(MASONRY.DATA_ATTRS.DESKTOP_COLUMNS)) ||
        parseInt(containerEl.parentElement.getAttribute(MASONRY.DATA_ATTRS.DESKTOP_COLUMNS)) ||
        MASONRY.DEFAULTS.DESKTOP_COLUMNS;
    const mobileColumnCount =
        parseInt(containerEl.getAttribute(MASONRY.DATA_ATTRS.MOBILE_COLUMNS)) ||
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
    const desktopColSpan = Math.floor(12 / desktopColumnCount);
    const mobileColSpan = Math.floor(12 / mobileColumnCount);

    const columnEls = Array.from(
        { length: Math.max(desktopColumnCount, mobileColumnCount) },
        () => {
            const columnEl = document.createElement("div");
            columnEl.classList.add(
                MASONRY.CLASSES.COLUMN,
                MASONRY.CLASSES.NOT_SELECTABLE,
                `col-${mobileColSpan}`,
                `col-lg-${desktopColSpan}`
            );
            return columnEl;
        }
    );

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
 * Retrieves the index of an element based on a defined data attribute.
 * If the element is wrapped in a container (e.g., an anchor tag), it checks the
 * first child element for the index.
 *
 * @private
 * @param {Element} el - The element or wrapper to retrieve the index from.
 * @returns {number} The numeric value of the index, or Infinity if no index
 *                   is found.
 */
function _getElementIndex(el) {
    if (el.hasAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX)) {
        return Number(el.getAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX));
    }

    // Handle case where the element is wrapped in a container (e.g. anchor tag)
    const firstChildEl = el.firstElementChild;
    if (firstChildEl && firstChildEl.hasAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX)) {
        return Number(firstChildEl.getAttribute(MASONRY.DATA_ATTRS.ITEM_INDEX));
    }

    return Infinity; // Ensure elements without an index appear last
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

    // Check if the row contains only masonry columns (masonry mode applied)
    // If true, get elements from inside the columns; otherwise, use row's
    // direct children
    const isMasonryMode = Array.from(rowEl.children).every((child) =>
        child.classList.contains(MASONRY.CLASSES.COLUMN)
    );
    const originalEls = isMasonryMode
        ? Array.from(rowEl.children).flatMap((columnEl) => Array.from(columnEl.children))
        : Array.from(rowEl.children);

    return originalEls.sort(
        (firstEl, secondEl) => _getElementIndex(firstEl) - _getElementIndex(secondEl)
    );
}

/**
 * Creates the masonry layout by organizing elements one by one in the
 * shortest column.
 *
 * @param {Element} rowEl - The row element containing the items to organize
 * @param {number} desktopColumnCount - Number of columns for desktop view
 * @param {number} mobileColumnCount - Number of columns for mobile view
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
    rowEl.classList.add(MASONRY.CLASSES.ROW, MASONRY.CLASSES.FIXED_COLUMNS);

    // Distribute items across the columns
    for (const el of originalEls) {
        el.classList.add(MASONRY.CLASSES.ITEM);

        // Get the shortest column and append the element to it
        const shortestColumnEl = _getShortestColumn(columnEls);
        shortestColumnEl.appendChild(el);

        // Wait for all images in the shortest column to load before continuing
        // to ensure next shortest column is correctly calculated
        // TODO: move onceAllImagesLoaded in web_editor and to use it here
        const imageEls = shortestColumnEl.querySelectorAll("img");
        await Promise.all(
            Array.from(imageEls).map(
                (imgEl) =>
                    new Promise((resolve) => {
                        if (imgEl.complete) {
                            resolve();
                        } else {
                            imgEl.onload = resolve;
                        }
                    })
            )
        );
    }
}

/**
 * Toggles the masonry layout mode for the given container element.
 * Ensures the container has a `.row` element, which acts as the parent for
 * masonry columns.
 *
 * @public
 * @param {Element} containerEl - Container element with the class in
 *                                MASONRY.CLASSES.CONTAINER_CLASSES, consisting
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
 * Checks if the given section element follows a valid masonry layout structure.
 *
 * @param {HTMLElement} sectionEl - The root section element to validate.
 * @returns {boolean} True if the masonry layout structure is valid,
 *                    otherwise false.
 */
export function isValidMasonryLayout(sectionEl) {
    if (!sectionEl || !sectionEl.classList.contains(MASONRY.CLASSES.MODE)) {
        return false;
    }

    const containerEl = sectionEl.firstElementChild;
    if (!containerEl) {
        return false;
    }

    const isContainerClass = MASONRY.CLASSES.CONTAINER_CLASSES.some((containerClass) =>
        containerEl.classList.contains(containerClass)
    );
    if (!isContainerClass) {
        return false;
    }

    const rowEl = containerEl.firstElementChild;
    if (!rowEl || !rowEl.classList.contains(MASONRY.CLASSES.ROW)) {
        return false;
    }

    const columnEls = rowEl.children;
    const allColumnsValid = Array.from(columnEls).every((columnEl) =>
        columnEl.classList.contains(MASONRY.CLASSES.COLUMN)
    );
    if (!allColumnsValid) {
        return false;
    }

    return true;
}

/**
 * Clears the masonry layout
 *
 * @public
 * @param {Element} sectionEl - Root element containing the masonry layout
 */
export function clearMasonryLayout(sectionEl) {
    if (!sectionEl) {
        return;
    }

    if (!isValidMasonryLayout(sectionEl)) {
        return;
    }

    sectionEl.classList.remove(MASONRY.CLASSES.MODE);

    const containerEl = sectionEl.firstElementChild;
    const rowEl = containerEl.firstElementChild;
    rowEl.classList.remove(MASONRY.CLASSES.ROW, MASONRY.CLASSES.FIXED_COLUMNS);

    const originalEls = Array.from(rowEl.children)
        .flatMap((columnEl) => Array.from(columnEl.children))
        .sort((firstEl, secondEl) => _getElementIndex(firstEl) - _getElementIndex(secondEl));

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
    if (rowEl && rowEl.classList.contains(MASONRY.CLASSES.ROW)) {
        toggleMasonryMode(containerEl);
    }
}

/**
 * Creates a resize observer for automatically updating masonry layout when the
 * screen size changes.
 *
 * @public
 * @param {Element} sectionEl - The section element to observe.
 * @param {number} debounceTime - Debounce time in milliseconds.
 * @returns {ResizeObserver|null} The resize observer instance,
 *                                or null if masonry element is not found.
 * @default debounceTime 100
 */
export function observeMasonryLayoutWidthChange(sectionEl, debounceTime = 100) {
    if (!sectionEl) {
        return null;
    }

    if (!isValidMasonryLayout(sectionEl)) {
        return null;
    }

    const masonryContainerEl = sectionEl.firstElementChild;
    const masonryRowEl = masonryContainerEl.firstElementChild;

    let lastWidth = masonryRowEl.offsetWidth;
    const resizeObserver = new ResizeObserver(
        debounce(() => {
            const newWidth = masonryRowEl.offsetWidth;
            // Only trigger when width has changed
            if (newWidth !== lastWidth) {
                lastWidth = newWidth;
                toggleMasonryMode.call(this, masonryContainerEl);
            }
        }, debounceTime)
    );
    resizeObserver.observe(masonryRowEl);

    return resizeObserver;
}
