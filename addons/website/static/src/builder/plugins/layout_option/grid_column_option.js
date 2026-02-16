import { BaseOptionComponent } from "@html_builder/core/utils";

export class GridColumnsOption extends BaseOptionComponent {
    static template = "website.GridColumnsOption";
    static selector = ".row.o_grid_mode > div.o_grid_item";
}
