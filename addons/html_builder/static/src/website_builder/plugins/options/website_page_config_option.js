import { BaseOptionComponent } from "@html_builder/core/utils";

export class TopMenuVisibilityOption extends BaseOptionComponent {
    static template = "html_builder.TopMenuVisibilityOption";
    static props = {
        doesPageOptionExist: Function,
    };
}
