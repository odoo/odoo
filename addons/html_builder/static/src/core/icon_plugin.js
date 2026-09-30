import { IconPlugin as EditorIconPlugin } from "@html_editor/main/media/icon_plugin";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";

export class IconPlugin extends EditorIconPlugin {
    toolbarNamespace = DISABLED_NAMESPACE;
}
