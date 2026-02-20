import { ImageToolOptionPlugin } from "@html_builder/plugins/image/image_tool_option_plugin";
import { registry } from "@web/core/registry";

// Temporary override: the `ImageToolOptionPlugin`'s options are not actually
// used in translate mode. Grep @image-translate.
export class TranslationImageToolOptionPlugin extends ImageToolOptionPlugin {
    resources = Object.assign(this.resources, { builder_options: [] });
}

registry
    .category("translation-plugins")
    .add(TranslationImageToolOptionPlugin.id, TranslationImageToolOptionPlugin);
