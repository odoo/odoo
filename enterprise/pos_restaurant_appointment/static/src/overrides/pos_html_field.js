import { patch } from "@web/core/utils/patch";
import { htmlField } from "@html_editor/fields/html_field";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { HintPlugin } from "@html_editor/main/hint_plugin";

// The goal is to create a minimal html editor for the point_of_sale environment
patch(htmlField, {
    extractProps() {
        const data = super.extractProps(...arguments);
        data.editorConfig = {
            ...data.editorConfig,
            Plugins: [...CORE_PLUGINS, HintPlugin],
        };
        return data;
    },
});
