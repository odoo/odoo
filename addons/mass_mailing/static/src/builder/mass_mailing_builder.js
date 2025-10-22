import { Component, useSubEnv } from "@odoo/owl";
import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS } from "@html_builder/core/core_plugins";
import { removePlugins } from "@html_builder/utils/utils";
import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";
import { registry } from "@web/core/registry";

export class MassMailingBuilder extends Component {
    static template = "mass_mailing.MassMailingBuilder";
    static components = { Builder };
    static props = {
        builderProps: { type: Object },
        toggleCodeView: { type: Function, optional: true },
        toggleFullScreen: { type: Function },
    };

    setup() {
        const originalOverlay = this.env.services.overlay;
        const subServices = Object.create(this.env.services);
        subServices.overlay = Object.create(originalOverlay);
        subServices.overlay.add = (c, props, opts = {}) => {
            // The builder will use this new overlay that will guarantee:
            // 1. Internal ordering of its different overlays
            // 2. To not messup with owl's reconciliation of foreach when adding/removing overlays
            // This is a sub-optimal fix to the more general issue of owl displacing nodes that contain
            // an iframe, in which the iframe effectively unloads.
            opts = {
                ...opts,
                sequence: (opts.sequence ?? 50) + 1000,
            }
            return originalOverlay.add(c, props, opts);
        }
        useSubEnv({ services: subServices });
    }

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
