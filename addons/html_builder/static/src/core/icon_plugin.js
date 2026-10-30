import { IconPlugin as EditorIconPlugin } from "@html_editor/main/media/icon_plugin";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";
import { isIconElement } from "@html_editor/utils/dom_info";

export class IconPlugin extends EditorIconPlugin {
    resources = {
        ...this.resources,
        properties: [
            // Before the parent's declarations: the first matching `toolbar` wins.
            { predicate: isIconElement, toolbar: DISABLED_NAMESPACE },
            ...this.resources.properties,
        ],
    };
}
