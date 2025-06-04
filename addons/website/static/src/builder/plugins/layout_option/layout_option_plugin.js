import { getRow } from "@html_builder/utils/column_layout_utils";
import {
    convertToNormalColumn,
    reloadLazyImages,
    toggleGridMode,
} from "@html_builder/utils/grid_layout_utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { LayoutGridOption, LayoutOption } from "./layout_option";
import { withSequence } from "@html_editor/utils/resource";
import { LAYOUT, LAYOUT_GRID } from "@website/builder/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

class LayoutOptionPlugin extends Plugin {
    static id = "LayoutOption";
    static dependencies = ["clone", "selection"];
    resources = {
        builder_options: [
            withSequence(LAYOUT, {
                OptionComponent: LayoutOption,
                selector:
                    "section, section.s_carousel_wrapper .carousel-item, .s_carousel_intro_item",
                exclude:
                    ".s_dynamic, .s_dynamic_snippet_content, .s_dynamic_snippet_title, .s_masonry_block, .s_framed_intro, .s_features_grid, .s_media_list, .s_table_of_content, .s_process_steps, .s_image_gallery, .s_pricelist_boxed, .s_quadrant, .s_pricelist_cafe, .s_faq_horizontal, .s_image_frame, .s_card_offset, .s_contact_info, .s_tabs, .s_tabs_images, .s_floating_blocks .s_floating_blocks_block, .s_banner_categories",
                applyTo: ":scope > *:has(> .row), :scope > .s_allow_columns",
            }),
            withSequence(LAYOUT_GRID, {
                OptionComponent: LayoutGridOption,
                selector:
                    "section.s_masonry_block, section.s_quadrant, section.s_image_frame, section.s_card_offset, section.s_contact_info, section.s_framed_intro, section.s_banner_categories",
                applyTo: ":scope > *:has(> .row)",
            }),
        ],
        on_cloned_handlers: this.onCloned.bind(this),
        builder_actions: {
            SetGridLayoutAction,
            SetColumnLayoutAction,
        },
    };
    onCloned({ cloneEl }) {
        const cloneElClassList = cloneEl.classList;
        const offsetClasses = [...cloneElClassList].filter((cls) =>
            cls.match(/^offset-(lg-)?([0-9]{1,2})$/)
        );
        cloneElClassList.remove(...offsetClasses);
    }
}

const isGrid = (el) => {
    const rowEl = getRow(el);
    return !!(rowEl && rowEl.classList.contains("o_grid_mode"));
};
export class SetGridLayoutAction extends BuilderAction {
    static id = "setGridLayout";
    static dependencies = ["selection"];
    apply({ editingElement }) {
        // TODO no preview/apply if it s isApplied
        if (isGrid(editingElement)) {
            return;
        }
        toggleGridMode(
            editingElement,
            this.dependencies.selection.preserveSelection,
            this.config.mobileBreakpoint
        );
    }
    isApplied({ editingElement }) {
        return isGrid(editingElement);
    }
}
export class SetColumnLayoutAction extends BuilderAction {
    static id = "setColumnLayout";
    apply({ editingElement }) {
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
            convertToNormalColumn(columnEl, this.config.mobileBreakpoint);
        }
        // Removing the grid properties.
        delete rowEl.dataset.rowCount;
        // Kept for compatibility.
        rowEl.style.removeProperty("--grid-item-padding-x");
        rowEl.style.removeProperty("--grid-item-padding-y");
        rowEl.style.removeProperty("gap");
    }
    isApplied({ editingElement }) {
        return !isGrid(editingElement);
    }
}
registry.category("website-plugins").add(LayoutOptionPlugin.id, LayoutOptionPlugin);
