import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Detects when a category section becomes visible within a scrollable container.
 *
 * @param {string} categoryId - Initial selected category id
 * @param {Object} categoryScrollContainerRef - Ref to the scrollable container holding the category names
 * @param {Object} productScrollContainerRef - Ref to the scrollable container holding the product items grouped by categories
 * @param {Function} [getScrollCategories] - Function that returns the list of categories with their top position and their id.
 * @param {Function} [onCategoryVisible=() => {}] - Callback invoked when the category becomes visible
 * @param {Object} [options={}]
 * @param {number} [options.categoryScrollOffsetLeft=-5] - Horizontal scroll offset applied when scrolling to a category name
 * @param {number} [options.productScrollOffsetTop=-15] - Vertical offset applied when scrolling to a product section
 * @param {number} [options.visibleThreshold=100] - Minimum number of pixels from the top of the container a category must be visible to be considered active
 */

export function useCategoryScrollSpy(
    categoryId,
    categoryScrollContainerRef,
    productScrollContainerRef,
    getScrollCategories,
    onCategoryVisible = () => {},
    options = {}
) {
    const {
        categoryScrollOffsetLeft = 0,
        productScrollOffsetTop = -5,
        visibleThreshold = 100,
    } = options;

    let isScrolling = false;

    let selectedCategoryId = categoryId;

    function selectCategory(categoryId) {
        selectedCategoryId = categoryId;
        onCategoryVisible(selectedCategoryId);
        const tabEl = categoryScrollContainerRef.el.querySelector(
            `[data-category-pill="${categoryId}"]`
        );
        if (tabEl) {
            const scrollLeft = tabEl.offsetLeft + categoryScrollOffsetLeft;
            categoryScrollContainerRef.el.scrollTo({
                left: scrollLeft || 0,
                behavior: "smooth",
            });
        }
    }

    function scrollToCategory(categoryId) {
        const scrollCategory = getScrollCategories().find((category) => category.id === categoryId);
        const { el: scrollEl } = productScrollContainerRef;

        if (scrollCategory) {
            scrollEl.scrollTo({ top: scrollCategory.top + productScrollOffsetTop });
        }

        //Ensure the category is correctly selected and visible
        selectCategory(categoryId);
    }

    function onProductScroll() {
        let topCategoryId = null;
        const containerTop = productScrollContainerRef.el.scrollTop;
        const containerTopThreshold = containerTop + visibleThreshold;
        const scrollCategories = getScrollCategories();

        // Loop until one category is above the threshold
        // And take the previous one as the top category
        for (let i = 0; i < scrollCategories.length; i++) {
            const scrollCategory = scrollCategories[i];
            const categoryTop = scrollCategory.top;

            if (categoryTop > containerTopThreshold) {
                topCategoryId = scrollCategories[i - 1]?.id || null;
                break;
            }
        }

        if (topCategoryId !== null && selectedCategoryId !== topCategoryId) {
            selectCategory(topCategoryId);
        }
    }

    function deferScroll() {
        if (!isScrolling) {
            isScrolling = true;
            requestAnimationFrame(() => {
                onProductScroll();
                isScrolling = false;
            });
        }
    }

    onMounted(() => {
        productScrollContainerRef.el.addEventListener("scroll", deferScroll);
        onProductScroll();
    });

    onWillUnmount(() => {
        productScrollContainerRef.el.removeEventListener("scroll", deferScroll);
    });

    return {
        scrollToCategory,
    };
}
