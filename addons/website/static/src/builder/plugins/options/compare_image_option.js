import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { DependencyManager } from "@html_builder/core/dependency_manager";
import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { MediaSizeOption } from "@html_builder/plugins/image/media_size_option";
import { ReplaceMediaOption } from "@html_builder/plugins/image/replace_media_option";
import { registry } from "@web/core/registry";
import { useSubEnv } from "@web/owl2/utils";

export class CompareImageToolOption extends ImageToolOption {
    static template = "website.CompareImageToolOption";
    static components = { ...ImageToolOption.components, ReplaceMediaOption };

    setup() {
        // Both images' options use the same item ids (link, crop, transform),
        // so each image gets its own scope, or its buttons would follow the
        // other image's state.
        useSubEnv({ dependencyManager: new DependencyManager() });
        super.setup();
    }
}

export class CompareImageOption extends BaseOptionComponent {
    static id = "compare_image_option";
    static template = "website.CompareImageOption";
    static components = {
        CompareImageToolOption,
        MediaSizeOption,
    };
}

registry.category("website-options").add(CompareImageOption.id, CompareImageOption);
