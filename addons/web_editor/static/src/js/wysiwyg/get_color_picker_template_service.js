
/** @odoo-module **/
import { registry } from "@web/core/registry";

let colorPickerTemplatePromise;
export const getColorPickerTemplateService = {
    dependencies: ["orm"],
    async: true,
    start(env, { orm }) {
        return () => {
            colorPickerTemplatePromise ??= orm.call(
                'ir.ui.view',
                'render_public_asset',
                ['web_editor.colorpicker', {}]
            );
            return colorPickerTemplatePromise;
        };
    },
};

registry.category("services").add("get_color_picker_template", getColorPickerTemplateService);
