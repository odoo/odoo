import { getFirstItem, getNbColumns } from "@html_builder/utils/column_layout_utils";
import {
    convertToNormalColumn,
    reloadLazyImages,
    toggleGridMode,
} from "@html_builder/utils/grid_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { LayoutOption } from "./layout_option";

class LayoutOptionPlugin extends Plugin {
    static id = "LayoutOption";
    static dependencies = ["clone"];
    resources = {
        builder_options: {
            OptionComponent: LayoutOption,
            selector:
                ":is(section, section.s_carousel_wrapper .carousel-item, .s_carousel_intro_item):has(> * > .row, > .s_allow_columns)",
            exclude:
                ".s_dynamic, .s_dynamic_snippet_content, .s_dynamic_snippet_title, .s_masonry_block, .s_framed_intro, .s_features_grid, .s_media_list, .s_table_of_content, .s_process_steps, .s_image_gallery, .s_timeline, .s_pricelist_boxed, .s_quadrant, .s_pricelist_cafe, .s_faq_horizontal, .s_image_frame, .s_card_offset, .s_contact_info, .s_tabs",
        },

        builder_actions: this.getActions(),
    };

    getActions() {
        const getRow = (el) => el.querySelector(":scope > .container > .row");
        const isGrid = (el) => {
            const rowEl = getRow(el);
            return !!(rowEl && rowEl.classList.contains("o_grid_mode"));
        };
        return {
            setGridLayout: {
                apply: ({ editingElement }) => {
                    // TODO no preview/apply if it s isApplied
                    if (isGrid(editingElement)) {
                        return;
                    }
                    toggleGridMode(editingElement.querySelector(".container"));
                },
                isApplied: ({ editingElement }) => isGrid(editingElement),
            },
            setColumnLayout: {
                apply: ({ editingElement }) => {
                    const rowEl = getRow(editingElement);
                    // TODO no preview/apply if it s isApplied
                    if (!isGrid(editingElement)) {
                        return;
                    }

                    // Removing the grid class
                    rowEl.classList.remove("o_grid_mode");
                    const columnEls = rowEl.children;

                    for (const columnEl of columnEls) {
                        // Reloading the images.
                        reloadLazyImages(columnEl);
                        // Removing the grid properties.
                        convertToNormalColumn(columnEl);
                    }
                    // Removing the grid properties.
                    delete rowEl.dataset.rowCount;
                    // Kept for compatibility.
                    rowEl.style.removeProperty("--grid-item-padding-x");
                    rowEl.style.removeProperty("--grid-item-padding-y");
                    rowEl.style.removeProperty("gap");
                },
                isApplied: ({ editingElement }) => !isGrid(editingElement),
            },
            changeColumnCount: {
                apply: ({ editingElement, value: nbColumns }) => {
                    if (nbColumns === "custom") {
                        return;
                    }
                    const rowEl = getRow(editingElement);
                    const columnEls = rowEl.children;
                    const prevNbColumns = getNbColumns(columnEls, isMobileView(this.editable));

                    if (nbColumns === prevNbColumns) {
                        return;
                    }
                    this.resizeColumns(columnEls, nbColumns);

                    const itemsDelta = nbColumns - rowEl.children.length;
                    if (itemsDelta > 0) {
                        for (let i = 0; i < itemsDelta; i++) {
                            const lastEl = rowEl.lastElementChild;
                            this.dependencies.clone.cloneElement(lastEl);
                        }
                    }
                },
                isApplied: ({ editingElement, value }) => {
                    const columnEls = getRow(editingElement)?.children;
                    return getNbColumns(columnEls, isMobileView(this.editable)) === value;
                },
            },
        };
    }

    /**
     * Resizes the columns for the mobile or desktop view.
     *
     * @private
     * @param {HTMLCollection} columnEls - the elements to resize
     * @param {integer} nbColumns - the number of wanted columns
     */
    resizeColumns(columnEls, nbColumns) {
        const isMobile = isMobileView(this.editable);
        const itemSize = Math.floor(12 / nbColumns) || 1;
        const firstItem = getFirstItem(columnEls, isMobile);
        const firstItemOffset = Math.floor((12 - itemSize * nbColumns) / 2);

        const resolutionModifier = isMobile ? "" : "-lg";
        const replacingRegex =
            // (?!\S): following char cannot be a non-space character
            new RegExp(`(?:^|\\s+)(col|offset)${resolutionModifier}(-\\d{1,2})?(?!\\S)`, "g");

        for (const columnEl of columnEls) {
            columnEl.className = columnEl.className.replace(replacingRegex, "");
            columnEl.classList.add(`col${resolutionModifier}-${itemSize}`);
            if (firstItemOffset && columnEl === firstItem) {
                columnEl.classList.add(`offset${resolutionModifier}-${firstItemOffset}`);
            }
            const hasMobileOffset = columnEl.className.match(/(^|\s+)offset-\d{1,2}(?!\S)/);
            const hasDesktopOffset = columnEl.className.match(/(^|\s+)offset-lg-[1-9][0-1]?(?!\S)/);
            columnEl.classList.toggle("offset-lg-0", hasMobileOffset && !hasDesktopOffset);
        }
    }
}
registry.category("website-plugins").add(LayoutOptionPlugin.id, LayoutOptionPlugin);
