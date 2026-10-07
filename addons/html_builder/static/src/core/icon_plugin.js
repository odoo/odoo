import { IconPlugin as EditorIconPlugin } from "@html_editor/main/media/icon_plugin";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";
import { isIconElement } from "@html_editor/utils/dom_info";

export class IconPlugin extends EditorIconPlugin {
    resources = {
        ...this.resources,
        region_properties: { is: isIconElement, toolbar: DISABLED_NAMESPACE },
    };
}
