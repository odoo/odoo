import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS as CORE_BUILDER_PLUGINS } from "@html_builder/core/core_plugins";
import { removePlugins } from "@html_builder/utils/utils";
import { MAIN_PLUGINS as MAIN_EDITOR_PLUGINS } from "@html_editor/plugin_sets";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";

export class MassMailingBuilder extends Component {
    static template = "mass_mailing_egg.MassMailingBuilder";
    static components = { Builder };
    static props = {
        builderProps: { type: Object },
    };

    get builderProps() {
        const builderProps = Object.assign({}, this.props.builderProps);
        const massMailingPlugins = [
            ...registry.category("builder-plugins").getAll(),
            // TODO EGGMAIL: use this registry for mass_mailing exclusive plugins
            ...registry.category("mass_mailing-plugins").getAll(),
        ];
        // TODO EGGMAIL: copied from website, check if something needs to be changed here
        const mainEditorPluginsToRemove = [
            "PowerButtonsPlugin",
            "DoubleClickImagePreviewPlugin",
            "StarPlugin",
            "BannerPlugin",
            "MoveNodePlugin",
        ];
        const mainEditorPlugins = removePlugins(
            [...MAIN_EDITOR_PLUGINS],
            mainEditorPluginsToRemove
        );
        const coreBuilderPluginsToRemove = ["SavePlugin"];
        const builderEditorPlugins = removePlugins(
            [...CORE_BUILDER_PLUGINS],
            coreBuilderPluginsToRemove
        );
        const optionalPlugins = [
            ...(this.props.builderProps.config.dynamicPlaceholder
                ? DYNAMIC_PLACEHOLDER_PLUGINS
                : []),
        ];
        const Plugins = [
            ...mainEditorPlugins,
            ...builderEditorPlugins,
            ...massMailingPlugins,
            ...optionalPlugins,
        ];
        builderProps.Plugins = Plugins;
        return builderProps;
    }
}

registry.category("lazy_components").add("mass_mailing_egg.MassMailingBuilder", MassMailingBuilder);
