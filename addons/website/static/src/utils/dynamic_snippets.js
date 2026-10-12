// Utilities for managing the number of elements per row in dynamic carousel
// snippets.
export const DYNAMIC_SNIPPET_DEFAULT_ITEMS_PER_ROW_LEFT_TITLE = 2;
export const DYNAMIC_SNIPPET_DEFAULT_ITEMS_PER_ROW = 4;
export const DYNAMIC_SNIPPET_DEFAULT_ITEMS_PER_ROW_SM = 1;

export function updateDynamicCarouselNumberOfElements(editingElement) {
    const dynamicCarouselEl = editingElement.closest(".o_dynamic_carousel_snippet");
    if (!dynamicCarouselEl) {
        return;
    }
    const hasTitleAside = !!dynamicCarouselEl.querySelector(".s_dynamic_snippet_title_aside");
    const isContainerFluid = !!dynamicCarouselEl.querySelector(".container-fluid");

    dynamicCarouselEl.dataset.numberOfElements =
        hasTitleAside && !isContainerFluid
            ? DYNAMIC_SNIPPET_DEFAULT_ITEMS_PER_ROW_LEFT_TITLE
            : DYNAMIC_SNIPPET_DEFAULT_ITEMS_PER_ROW;
}
