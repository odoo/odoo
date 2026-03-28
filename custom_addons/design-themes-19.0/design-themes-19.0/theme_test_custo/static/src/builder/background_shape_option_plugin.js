import { BackgroundShapeOptionPlugin } from "@html_builder/plugins/background_option/background_shape_option_plugin";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(BackgroundShapeOptionPlugin.prototype, {
    getBackgroundShapeGroups() {
        const bgShapeGroups = super.getBackgroundShapeGroups();
        bgShapeGroups.basic.subgroups["custom_shape"] = {
            label: "Custom Shapes",
            shapes: {
                "theme_test_custo/curves/01": {
                    selectLabel: _t("Curve 01"),
                    transform: false,
                    togglableRatio: true,
                },
            },
        };
        return bgShapeGroups;
    },
});
