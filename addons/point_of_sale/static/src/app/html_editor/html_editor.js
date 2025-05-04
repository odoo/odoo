import { HtmlField } from "@html_editor/fields/html_field";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { patch } from "@web/core/utils/patch";

patch(HtmlField.prototype, {
    getConfig() {
        const config = super.getConfig();
        return {
            ...config,
            Plugins: CORE_PLUGINS,
        };
    },
});
