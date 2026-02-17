import { CropImageAction } from "@html_builder/plugins/image/image_tool_option_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { patch } from "@web/core/utils/patch";


patch(CropImageAction.prototype, {
    setup() {
        super.setup();
        this.withLoadingEffect =
            closestElement(this.editable, ".o_mass_mailing_with_builder") !== null;
    },
});
