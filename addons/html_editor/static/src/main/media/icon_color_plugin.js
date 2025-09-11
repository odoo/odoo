import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { ColorSelector } from "../font/color_selector";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class IconColorPlugin extends Plugin {
    static id = "iconColor";
    static dependencies = ["icon", "colorUi"];
    resources = {
        toolbar_groups: withSequence(1, { id: "icon_color", namespaces: ["icon"] }),
        toolbar_items: [
            {
                id: "icon_forecolor",
                groupId: "icon_color",
                description: _t("Select Font Color"),
                Component: ColorSelector,
                props: this.dependencies.colorUi.getPropsForColorSelector("foreground"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "icon_backcolor",
                groupId: "icon_color",
                description: _t("Select Background Color"),
                Component: ColorSelector,
                props: this.dependencies.colorUi.getPropsForColorSelector("background"),
                isAvailable: isHtmlContentSupported,
            },
        ],
    };
}
