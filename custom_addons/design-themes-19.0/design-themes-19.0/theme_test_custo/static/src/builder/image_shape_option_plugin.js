import { ImageShapeOptionPlugin } from "@html_builder/plugins/image/image_shape_option_plugin";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ImageShapeOptionPlugin.prototype, {
    getImageShapeGroups() {
        const imageShapeGroups = super.getImageShapeGroups();
        imageShapeGroups.basic.subgroups["custom_shape"] = {
            label: "Custom Shapes",
            shapes: {
                "theme_test_custo/blob/01": {
                    selectLabel: _t("Blob 01"),
                    transform: false,
                    togglableRatio: true,
                },
            },
        };
        return imageShapeGroups;
    },
});
