import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";
import { useDomState } from "../builder_helpers";
import { SpacingOption } from "./spacing_option";
import { AddElementOption } from "./add_element_option";

// TODO to import in html_builder
import {
    _convertToNormalColumn,
    _reloadLazyImages,
    _toggleGridMode,
} from "@web_editor/js/common/grid_layout_utils";

export class LayoutOption extends Component {
    static template = "html_builder.LayoutOption";
    static components = { ...defaultOptionComponents, SpacingOption, AddElementOption };

    setup() {
        this.state = useDomState(() => ({
            elementLayout: this.isGrid() ? "grid" : "column",
            columnCount: this.getRow()?.children.length,
        }));
    }
    getRow() {
        return this.env.editingElement.querySelector(".row");
    }
    isGrid() {
        const rowEl = this.getRow();
        return rowEl && rowEl.classList.contains("o_grid_mode");
    }
    setGridLayout() {
        if (this.isGrid()) {
            // Prevent toggling grid mode twice.
            return;
        }
        _toggleGridMode(this.env.editingElement.querySelector(".container"));
        this.env.editor.shared.history.addStep();
    }
    setColumnLayout() {
        // Toggle normal mode only if grid mode was activated (as it's in
        // normal mode by default).
        if (!this.isGrid()) {
            return;
        }
        const rowEl = this.getRow();

        // Removing the grid class
        rowEl.classList.remove("o_grid_mode");
        const columnEls = rowEl.children;

        for (const columnEl of columnEls) {
            // Reloading the images.
            _reloadLazyImages(columnEl);
            // Removing the grid properties.
            _convertToNormalColumn(columnEl);
        }
        // Removing the grid properties.
        delete rowEl.dataset.rowCount;
        // Kept for compatibility.
        rowEl.style.removeProperty("--grid-item-padding-x");
        rowEl.style.removeProperty("--grid-item-padding-y");
        rowEl.style.removeProperty("gap");
        // todo: should use the shared/dependencies/plugins instead when the cleaning PR is merged?
        this.env.editor.shared.history.addStep();
    }
    changeColumnCount(nbColumns) {
        console.warn(`changeColumnCount:`, nbColumns);
    }
}

registry.category("sidebar-element-toolbox").add("SectionToolbox", {
    ToolboxComponent: LayoutOption,
    selector: "section, section.s_carousel_wrapper .carousel-item, .s_carousel_intro_item",
    // TODO add exclude  data-exclude=".s_dynamic, .s_dynamic_snippet_content, .s_dynamic_snippet_title, .s_masonry_block, .s_framed_intro, .s_features_grid, .s_media_list, .s_table_of_content, .s_process_steps, .s_image_gallery, .s_timeline, .s_pricelist_boxed, .s_quadrant, .s_pricelist_cafe, .s_faq_horizontal, .s_image_frame, .s_card_offset, .s_contact_info"
    // TODO add target (applyTo) data-target="> *:has(> .row), > .s_allow_columns"
});
