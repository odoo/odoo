import { after, BLOCK_ALIGN } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class SizeOption extends BaseOptionComponent {
    static template = "html_builder.SizeOption";
    static selector = ".s_alert";
}

class SizeOptionPlugin extends Plugin {
    static id = "sizeOption";
    /** @type {import("plugins").ResourcesDeclarationsFactory} */
    resources = {
        builder_options: [withSequence(after(BLOCK_ALIGN), SizeOption)],
    };
}
registry.category("builder-plugins").add(SizeOptionPlugin.id, SizeOptionPlugin);
