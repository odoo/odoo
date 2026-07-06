import { onMounted, onWillUnmount } from "@odoo/owl";
import { resolveRefEl } from "@web/core/utils/ref_utils";

/**
 * Detects when a category section becomes visible within a scrollable container.
 *
 * @param {string} categoryId - Initial selected category id
 * @param {Object} categoryScrollContainerRef - Ref to the scrollable container holding the category names
 * @param {Object} productScrollContainerRef - Ref to the scrollable container holding the product items grouped by categories
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
    onCategoryVisible = () => {},
    options = {}
) {
    const {
        categoryScrollOffsetLeft = 0,
        productScrollOffsetTop = -5,
        visibleThreshold = 100,
    } = options;

    let categorySections = [];
    let isScrolling = false;

    let selectedCategoryId = categoryId;

    function selectCategory(categoryId) {
        selectedCategoryId = categoryId;
        onCategoryVisible(selectedCategoryId);
        const categoryScrollEl = resolveRefEl(categoryScrollContainerRef);
        const tabEl = categoryScrollEl.querySelector(`[data-category-pill="${categoryId}"]`);
        if (tabEl) {
            const scrollLeft = tabEl.offsetLeft + categoryScrollOffsetLeft;
            categoryScrollEl.scrollTo({
                left: scrollLeft || 0,
                behavior: "smooth",
            });
        }
    }

    function scrollToCategory(categoryId) {
        const section = categorySections.find((el) => el.dataset.category === "" + categoryId);
        const scrollEl = resolveRefEl(productScrollContainerRef);

        if (section) {
            const containerTop = scrollEl.getBoundingClientRect().top;
            const sectionTop = section.getBoundingClientRect().top;
            const scrollOffset =
                sectionTop - containerTop + scrollEl.scrollTop + productScrollOffsetTop;
            scrollEl.scrollTo({ top: scrollOffset });
        }

        //Ensure the category is correctly selected and visible
        selectCategory(categoryId);
    }

    function onProductScroll() {
        let topCategory = null;
        let minTop = Infinity;
        const containerTop =
            resolveRefEl(productScrollContainerRef).getBoundingClientRect().top + visibleThreshold;

        // Loop through each category section to determine which is closest to the top
        for (const section of categorySections) {
            const distanceFromTop = section.getBoundingClientRect().top - containerTop;
            const absDistanceFromTop = Math.abs(distanceFromTop);

            if (distanceFromTop <= 0 && absDistanceFromTop < minTop) {
                topCategory = section.dataset.category;
                minTop = absDistanceFromTop;
            } else if (distanceFromTop > 0) {
                if (!topCategory) {
                    topCategory = section.dataset.category;
                }
                break;
            }
        }

        const topCategoryId = Number(topCategory);
        if (selectedCategoryId !== topCategoryId) {
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
        const scrollEl = resolveRefEl(productScrollContainerRef);
        categorySections = [...scrollEl.querySelectorAll("[data-category]")];
        scrollEl.addEventListener("scroll", deferScroll);
        onProductScroll();
    });

    onWillUnmount(() => {
        resolveRefEl(productScrollContainerRef).removeEventListener("scroll", deferScroll);
    });

    return {
        scrollToCategory,
    };
}
