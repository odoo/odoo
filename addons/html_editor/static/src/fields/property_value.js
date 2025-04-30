import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { HtmlViewer } from "@html_editor/components/html_viewer/html_viewer";
import { localization } from "@web/core/l10n/localization";
import { patch } from "@web/core/utils/patch";
import { PropertyValue } from "@web/views/fields/properties/property_value";
import { normalizeHTML } from "@html_editor/utils/html";
import { Wysiwyg } from "@html_editor/wysiwyg";

patch(PropertyValue.prototype, {
    setup() {
        this.lastHtmlValue = this.propertyValue;
        return super.setup();
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

    /**
     * Wysiwyg key so when the value change, the component is reloaded.
     */
    get wysiwygKey() {
        return `${this.props.id}.${this.propertyValue}`;
    },

    getConfig() {
        return {
            content: this.propertyValue,
            debug: !!this.env.debug,
            direction: localization.direction || "ltr",
            placeholder: this.props.placeholder,
            Plugins: MAIN_PLUGINS,
            dropImageAsAttachment: true,
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
