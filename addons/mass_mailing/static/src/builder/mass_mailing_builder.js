import { Component } from "@odoo/owl";
import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS } from "@html_builder/core/core_plugins";
import { removePlugins } from "@html_builder/utils/utils";
import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";
import { registry } from "@web/core/registry";
import { CustomizeTab } from "@html_builder/sidebar/customize_tab";
import { OptionsContainerWithSnippetVersionControl } from "./options/options_container";

class CustomizeTabWithSnippetVersionControl extends CustomizeTab {
    static components = {
        ...CustomizeTab.components,
        OptionsContainer: OptionsContainerWithSnippetVersionControl,
    };
}

class BuilderWithSnippetVersionControl extends Builder {
    static components = {
        ...Builder.components,
        CustomizeTab: CustomizeTabWithSnippetVersionControl,
    };
}

export class MassMailingBuilder extends Component {
    static template = "mass_mailing.MassMailingBuilder";
    static components = { Builder: BuilderWithSnippetVersionControl };
    static props = {
        builderProps: { type: Object },
        toggleCodeView: { type: Function, optional: true },
        toggleFullScreen: { type: Function },
    };

    get builderProps() {
        const builderProps = Object.assign({}, this.props.builderProps);
        const massMailingPlugins = [
            ...registry.category("builder-plugins").getAll(),
            ...registry.category("mass_mailing-plugins").getAll(),
        ];
        const pluginsToRemove = [
            "BuilderFontPlugin", // Makes call to Google API (can't be used for emails)
            "SavePlugin",
            "SaveSnippetPlugin",
            "AnchorPlugin",
            "ColorUIPlugin",
            "EmbeddedFilePlugin",
            "FilePlugin",
            "AddDocumentsAttachmentPlugin",
        ];
        const builderEditorPlugins = removePlugins([...CORE_PLUGINS], pluginsToRemove);
        const optionalPlugins = [
            ...(this.props.builderProps.config.dynamicPlaceholder
                ? removePlugins(
                      DYNAMIC_PLACEHOLDER_PLUGINS,
                      ["PromptPlugin"] // mass_mailing does not use the dependency banner plugin
                  )
                : []),
        ];
        builderProps.Plugins = [...builderEditorPlugins, ...massMailingPlugins, ...optionalPlugins];
        return builderProps;
    }
}

registry.category("lazy_components").add("mass_mailing.MassMailingBuilder", MassMailingBuilder);
