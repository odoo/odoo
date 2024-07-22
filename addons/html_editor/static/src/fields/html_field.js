import {
    COLLABORATION_PLUGINS,
    MAIN_PLUGINS,
    DYNAMIC_PLACEHOLDER_PLUGINS,
    EMBEDDED_COMPONENT_PLUGINS,
} from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { READONLY_MAIN_EMBEDDINGS } from "@html_editor/readonly/embedded_components/embedding_sets";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { Component, useRef, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { HtmlViewer } from "./html_viewer";
import { TranslationButton } from "@web/views/fields/translation_button";

/**
 * Check whether the current value contains nodes that would break
 * on insertion inside an existing body.
 *
 * @returns {boolean} true if 'this.props.value' contains a node
 * that can only exist once per document.
 */
function computeContainsComplexHTML(value) {
    const domParser = new DOMParser();
    if (!value) {
        return false;
    }
    const parsedOriginal = domParser.parseFromString(value, "text/html");
    return !!parsedOriginal.head.innerHTML.trim();
}

export class HtmlField extends Component {
    static template = "html_editor.HtmlField";
    static props = {
        ...standardFieldProps,
        isCollaborative: { type: Boolean, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true, default: false },
        dynamicPlaceholderModelReferenceField: { type: String, optional: true },
        cssReadonlyAssetId: { type: String, optional: true },
        sandboxedPreview: { type: Boolean, optional: true },
        codeview: { type: Boolean, optional: true },
        editorConfig: { type: Object, optional: true },
        embeddedComponents: { type: Boolean, optional: true },
    };
    static defaultProps = {
        dynamicPlaceholder: false,
    };
    static components = {
        Wysiwyg,
        HtmlViewer,
        TranslationButton,
    };

    setup() {
        this.mutex = new Mutex();

        this.codeViewRef = useRef("codeView");

        const { model } = this.props.record;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () => this.commitChanges({ urgent: true }));
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges())
        );
        this.busService = this.env.services.bus_service;
        this.ormService = useService("orm");

        this.isDirty = false;
        this.state = useState({
            key: 0,
            showCodeView: false,
            containsComplexHTML: computeContainsComplexHTML(this.value),
        });
        this.lastValue = this.props.record.data[this.props.name].toString();
        useRecordObserver((record) => {
            // Reset Wysiwyg when we discard or onchange value
            if (!this.isDirty && this.lastValue !== record.data[this.props.name].toString()) {
                this.state.key++;
                this.state.containsComplexHTML = computeContainsComplexHTML(
                    record.data[this.props.name]
                );
            }
        });
        useRecordObserver((record) => {
            const value = record.data[this.props.dynamicPlaceholderModelReferenceField || "model"];
            // update Dynamic Placeholder reference model
            if (this.props.dynamicPlaceholder && this.editor) {
                this.editor.shared.updateDphDefaultModel?.(value);
            }
        });
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get displayReadonly() {
        return this.props.readonly || (this.sandboxedPreview && !this.state.showCodeView);
    }
    get wysiwygKey() {
        return `${this.props.record.resId}_${this.state.key}`;
    }

    get sandboxedPreview() {
        // @todo @phoenix maybe remove containsComplexHTML and alway use sandboxedPreview options
        return this.props.sandboxedPreview || this.state.containsComplexHTML;
    }

    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }

    async updateValue(value) {
        this.lastValue = value;
        this.isDirty = false;
        await this.props.record.update({ [this.props.name]: this.lastValue }).catch(() => {
            this.isDirty = true;
        });
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", this.isDirty);
    }

    async getEditorContent() {
        await this.editor.shared.savePendingImages();
        return this.editor.getElContent();
    }

    async _commitChanges({ urgent }) {
        if (this.isDirty) {
            if (this.state.showCodeView) {
                await this.updateValue(this.codeViewRef.el.value);
                return;
            }

            if (urgent) {
                await this.updateValue(this.editor.getContent());
            }
            const el = await this.getEditorContent();
            const content = el.innerHTML;
            if (!urgent || (urgent && this.lastValue !== content)) {
                await this.updateValue(content);
            }
        }
    }

    async commitChanges({ urgent } = {}) {
        if (urgent) {
            this._commitChanges({ urgent });
        } else {
            return this.mutex.exec(() => this._commitChanges({ urgent }));
        }
    }

    onEditorLoad(editor) {
        this.editor = editor;
    }

    onChange() {
        this.isDirty = true;
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
    }

    onBlur() {
        return this.commitChanges();
    }

    async toggleCodeView() {
        await this.commitChanges();
        this.state.showCodeView = !this.state.showCodeView;
    }

    getConfig() {
        const config = {
            content: this.value,
            Plugins: [
                ...MAIN_PLUGINS,
                ...(this.props.isCollaborative ? COLLABORATION_PLUGINS : []),
                ...(this.props.dynamicPlaceholder ? DYNAMIC_PLACEHOLDER_PLUGINS : []),
                ...(this.props.embeddedComponents ? EMBEDDED_COMPONENT_PLUGINS : []),
            ],
            classList: this.classList,
            onChange: this.onChange.bind(this),
            collaboration: this.props.isCollaborative && {
                busService: this.busService,
                ormService: this.ormService,
                collaborationChannel: {
                    collaborationModelName: this.props.record.resModel,
                    collaborationFieldName: this.props.name,
                    collaborationResId: parseInt(this.props.record.resId),
                },
                peerId: this.generateId(),
            },
            dropImageAsAttachment: true, // @todo @phoenix always true ?
            dynamicPlaceholder: this.dynamicPlaceholder,
            dynamicPlaceholderResModel:
                this.props.record.data[this.props.dynamicPlaceholderModelReferenceField || "model"],
            resources: {
                toolbarGroup: [
                    {
                        id: "codeview",
                        sequence: 100,
                        buttons: [
                            {
                                id: "codeview",
                                icon: "fa-code",
                                action: () => {
                                    this.toggleCodeView();
                                },
                            },
                        ],
                    },
                ],
            },
            direction: localization.direction || "ltr",
            getRecordInfo: () => {
                const { resModel, resId } = this.props.record;
                return { resModel, resId };
            },
            ...this.props.editorConfig,
        };

        if (this.props.embeddedComponents) {
            // TODO @engagement: fill this array with default/base components
            config.resources.embeddedComponents = MAIN_EMBEDDINGS;
        }

        const { sanitize_tags, sanitize } = this.props.record.fields[this.props.name];
        if (
            !("disableVideo" in config) &&
            (sanitize_tags || (sanitize_tags === undefined && sanitize))
        ) {
            config.disableVideo = true; // Tag-sanitized fields remove videos.
        }
        return config;
    }

    getReadonlyConfig() {
        const config = {
            value: this.value,
            cssAssetId: this.props.cssReadonlyAssetId,
            hasFullHtml: this.sandboxedPreview,
        };
        if (this.props.embeddedComponents) {
            config.embeddedComponents = READONLY_MAIN_EMBEDDINGS;
        }
        return config;
    }

    generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    }
}

export const htmlField = {
    component: HtmlField,
    displayName: _t("Html"),
    supportedTypes: ["html"],
    extractProps({ attrs, options }, dynamicInfo) {
        const editorConfig = {
            mediaModalParams: {
                useMediaLibrary: true,
            },
        };
        if (attrs.placeholder) {
            editorConfig.placeholder = attrs.placeholder;
        }
        if (options.height) {
            editorConfig.height = `${options.height}px`;
        }
        if ("disableImage" in options) {
            editorConfig.disableImage = Boolean(options.disableImage);
        }
        if ("disableVideo" in options) {
            editorConfig.disableVideo = Boolean(options.disableVideo);
        }
        return {
            editorConfig,
            isCollaborative: options.collaborative,
            dynamicPlaceholder: options.dynamic_placeholder,
            dynamicPlaceholderModelReferenceField:
                options.dynamic_placeholder_model_reference_field,
            embeddedComponents: options.embedded_components,
            sandboxedPreview: Boolean(options.sandboxedPreview),
            cssReadonlyAssetId: options.cssReadonly,
            codeview: Boolean(odoo.debug && options.codeview),
        };
    },
};

registry.category("fields").add("html", htmlField, { force: true });
