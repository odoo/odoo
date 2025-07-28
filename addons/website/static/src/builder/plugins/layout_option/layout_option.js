import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { AddElementOption } from "./add_element_option";
import { SpacingOption } from "./spacing_option";
import { layoutOptionSelector } from "@html_builder/utils/grid_layout_utils";

export class LayoutOption extends BaseOptionComponent {
    static template = "website.LayoutOption";
    static selector = layoutOptionSelector.selector;
    static exclude = layoutOptionSelector.exclude;
    static applyTo = layoutOptionSelector.applyTo;
    static components = {
        SelectNumberColumn,
        SpacingOption,
        AddElementOption,
    };
}

export class LayoutGridOption extends BaseOptionComponent {
    static template = "website.LayoutGridOption";
    static selector =
        "section.s_masonry_block, section.s_quadrant, section.s_image_frame, section.s_card_offset, section.s_contact_info, section.s_framed_intro";
    static applyTo = ":scope > *:has(> .row)";
    static components = {
        SpacingOption,
        AddElementOption,
    };
}
