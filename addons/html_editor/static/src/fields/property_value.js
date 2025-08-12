import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { HtmlViewer } from "@html_editor/components/html_viewer/html_viewer";
import { EditorVersionPlugin } from "@html_editor/core/editor_version_plugin";
import { localization } from "@web/core/l10n/localization";
import { patch } from "@web/core/utils/patch";
import { PropertyValue } from "@web/views/fields/properties/property_value";
import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";
import { normalizeHTML } from "@html_editor/utils/html";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { user } from "@web/core/user";
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";

patch(PropertyValue.prototype, {
    setup() {
        this.htmlUpgradeManager = new HtmlUpgradeManager();
        this.lastHtmlValue = this.propertyValue?.toString();
        onWillStart(async () => {
            this.htmlState.isPortalUser = await user.hasGroup("base.group_portal");
        });
        this.htmlState = useState({ isPortalUser: false, key: 0 });

        onWillUpdateProps((newProps) => {
            const newValueStr = newProps.value?.toString();
            if (newProps.type === "html" && newValueStr !== this.lastHtmlValue) {
                this.htmlState.key += 1;
                this.lastHtmlValue = newValueStr;
            }
        });

        return super.setup();
    },

    get propertyValue() {
        const value = super.propertyValue;
        return this.props.type === "html"
            ? this.htmlUpgradeManager.processForUpgrade(value || "")
            : value;
    },

    onEditorLoad(editor) {
        this.editor = editor;
    },

    async onEditorBlur() {
        const value = this.editor.getContent();
        if (normalizeHTML(value) !== normalizeHTML(this.lastHtmlValue)) {
            this.onValueChange(value);
            this.lastHtmlValue = value;
        }
    },

    onWysiwygChange() {
        if (!this.editor.editable.contains(document.activeElement)) {
            // The DOM of the Wysiwyg have been changed, while the user is not editing
            // (eg the chatgpt widget), mark the field as dirty
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
            this.onEditorBlur();
        }
    },

    getConfig() {
        let plugins = [...MAIN_PLUGINS, EditorVersionPlugin];
        if (this.htmlState.isPortalUser) {
            const toRemove = ["file", "media"];
            plugins = plugins.filter(
                (plugin) =>
                    !toRemove.some((p) => plugin.id === p || plugin.dependencies.includes(p))
            );
        }

        return {
            content: this.propertyValue,
            debug: !!this.env.debug,
            direction: localization.direction || "ltr",
            onChange: this.onWysiwygChange.bind(this),
            placeholder: this.props.placeholder,
            Plugins: plugins,
            dropImageAsAttachment: true,
            allowVideo: false,
            getRecordInfo: () => {
                const { resModel, resId, data, fields, id } = this.props.record;
                return { resModel, resId, data, fields, id };
            },
        };
    },

    getReadonlyConfig() {
        return {
            value: this.propertyValue,
            hasFullHtml: false,
            cssAssetId: "web.assets_frontend",
        };
    },
});

PropertyValue.components = { ...PropertyValue.components, HtmlViewer, Wysiwyg };
