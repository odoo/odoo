import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { after } from "@html_builder/utils/option_sequence";
import { HEADER_BOX } from "./header/header_option_plugin";

const LANGUAGE_SELECTOR = after(HEADER_BOX);
class LanguageSelectorOptionPlugin extends Plugin {
    static id = "languageSelectorOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            withSequence(LANGUAGE_SELECTOR, {
                template: "website.LanguageSelectorOption",
                editableOnly: false,
                selector: "#wrapwrap > header nav.navbar .o_header_language_selector",
                groups: ["website.group_website_designer"],
                reloadTarget: true,
            }),
        ],
    };
}

registry
    .category("website-plugins")
    .add(LanguageSelectorOptionPlugin.id, LanguageSelectorOptionPlugin);
