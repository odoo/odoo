import { BaseOptionComponent } from "@html_builder/core/utils";

export class TopMenuVisibilityOption extends BaseOptionComponent {
    static template = "website.TopMenuVisibilityOption";
    static props = {
        doesPageOptionExist: Function,
    };
}
