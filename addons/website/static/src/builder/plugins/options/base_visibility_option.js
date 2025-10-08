import { BaseOptionComponent } from "@html_builder/core/utils";

export class BaseVisibilityOption extends BaseOptionComponent {
    static template = "website.BaseVisibilityOption";
    static props = {
        action: { type: String, optional: true },
        bgColor: { type: String, optional: true },
        doesPageOptionExist: { type: Function, optional: true },
        label: { type: String },
        level: { type: Number, optional: true },
        overlay: { type: String, optional: true },
        setPageWebsiteDirtyAction: { type: String, optional: true },
        textColor: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        visibilityOpt: { type: String, optional: true },
    };
}
