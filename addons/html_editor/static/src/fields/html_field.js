import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";
import { stripVersion } from "@html_editor/html_migrations/html_migrations_utils";
import { stripHistoryIds } from "@html_editor/others/collaboration/collaboration_odoo_plugin";
import {
    COLLABORATION_PLUGINS,
    EMBEDDED_COMPONENT_PLUGINS,
    MAIN_PLUGINS,
} from "@html_editor/plugin_sets";
import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";
import {
    MAIN_EMBEDDINGS,
    READONLY_MAIN_EMBEDDINGS,
} from "@html_editor/others/embedded_components/embedding_sets";
import { normalizeHTML } from "@html_editor/utils/html";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { Component, markup, status, useRef, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TranslationButton } from "@web/views/fields/translation_button";
import { HtmlViewer } from "@html_editor/components/html_viewer/html_viewer";
import { EditorVersionPlugin } from "@html_editor/core/editor_version_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { fixInvalidHTML, instanceofMarkup } from "@html_editor/utils/sanitize";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

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
        collaborativeTrigger: { type: String, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true, default: false },
        dynamicPlaceholderModelReferenceField: { type: String, optional: true },
        migrateHTML: { type: Boolean, optional: true },
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
        this.htmlUpgradeManager = new HtmlUpgradeManager();
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
            containsComplexHTML: computeContainsComplexHTML(
                this.props.record.data[this.props.name]
            ),
        });

        useRecordObserver((record) => {
            // Reset Wysiwyg when we discard or onchange value
            const newValue = fixInvalidHTML(record.data[this.props.name]);
            if (!this.isDirty) {
                const value = normalizeHTML(newValue, this.clearElementToCompare.bind(this));
                if (this.lastValue !== value) {
                    this.state.key++;
                    this.state.containsComplexHTML = computeContainsComplexHTML(newValue);
                    this.lastValue = value;
                }
            }
        });
        useRecordObserver((record) => {
            const value = record.data[this.props.dynamicPlaceholderModelReferenceField || "model"];
            // update Dynamic Placeholder reference model
            if (this.props.dynamicPlaceholder && this.editor) {
                this.editor.shared.dynamicPlaceholder?.updateDphDefaultModel(value);
            }
        });
    }

    get value() {
        const value = this.props.record.data[this.props.name] || "";
        let newVal = fixInvalidHTML(value);
        if (this.props.migrateHTML) {
            newVal = this.htmlUpgradeManager.processForUpgrade(newVal, {
                containsComplexHTML: this.state.containsComplexHTML,
                env: this.env,
            });
        }
        if (instanceofMarkup(value)) {
            return markup(newVal);
        }
        return newVal;
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

    clearElementToCompare(element) {
        if (this.props.isCollaborative) {
            stripHistoryIds(element);
        }
        stripVersion(element);
    }

    async updateValue(value) {
        this.lastValue = normalizeHTML(value, this.clearElementToCompare.bind(this));
        this.isDirty = false;
        await this.props.record.update({ [this.props.name]: value }).catch(() => {
            this.isDirty = true;
        });
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", this.isDirty);
    }

    async getEditorContent() {
        await this.editor.shared.media?.savePendingImages();
        return this.editor.getElContent();
    }

    async _commitChanges({ urgent }) {
        if (status(this) === "destroyed") {
            return;
        }
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
            this.clearElementToCompare(el);
            const comparisonValue = el.innerHTML;
            if (!urgent || (urgent && this.lastValue !== comparisonValue)) {
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
        if (!this.state.showCodeView && this.editor) {
            this.editor.editable.innerHTML = this.value;
            this.editor.shared.history.addStep();
        }
    }

    getConfig() {
        const config = {
            content: this.value,
            Plugins: [
                ...(this.props.migrateHTML ? [EditorVersionPlugin] : []),
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
                collaborativeTrigger: this.props.collaborativeTrigger,
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
            direction: localization.direction || "ltr",
            getRecordInfo: () => {
                const { resModel, resId, data, fields, id } = this.props.record;
                return { resModel, resId, data, fields, id };
            },
            resources: {},
            ...this.props.editorConfig,
        };

        if (!("baseContainer" in config)) {
            config.baseContainer = "DIV";
        }

        if (this.props.embeddedComponents) {
            // TODO @engagement: fill this array with default/base components
            config.resources.embedded_components = [...MAIN_EMBEDDINGS];
        }

        const { sanitize_tags, sanitize } = this.props.record.fields[this.props.name];
        if (
            !("allowMediaDialogVideo" in config) &&
            (sanitize_tags || (sanitize_tags === undefined && sanitize))
        ) {
            config.allowMediaDialogVideo = false; // Tag-sanitized fields remove videos.
        }
        if (this.props.codeview) {
            config.resources = {
                ...config.resources,
                user_commands: [
                    {
                        id: "codeview",
                        description: _t("Code view"),
                        icon: "fa-code",
                        run: this.toggleCodeView.bind(this),
                        isAvailable: isHtmlContentSupported,
                    },
                ],
                toolbar_groups: withSequence(100, {
                    id: "codeview",
                }),
                toolbar_items: {
                    id: "codeview",
                    groupId: "codeview",
                    commandId: "codeview",
                },
            };
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
            config.embeddedComponents = [...READONLY_MAIN_EMBEDDINGS];
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
            editorConfig.classList = ["overflow-auto"];
        }
        if ("allowImage" in options) {
            editorConfig.allowImage = Boolean(options.allowImage);
        }
        if ("allowMediaDialogVideo" in options) {
            editorConfig.allowMediaDialogVideo = Boolean(options.allowMediaDialogVideo);
        }
        if ("allowFile" in options) {
            editorConfig.allowFile = Boolean(options.allowFile);
        }
        if ("allowAttachmentCreation" in options) {
            editorConfig.allowImage = Boolean(options.allowAttachmentCreation);
            editorConfig.allowFile = Boolean(options.allowAttachmentCreation);
        }
        if ("baseContainer" in options) {
            editorConfig.baseContainer = options.baseContainer;
        }
        if ("cleanEmptyStructuralContainers" in options) {
            editorConfig.cleanEmptyStructuralContainers = Boolean(
                options.cleanEmptyStructuralContainers
            );
        }
        return {
            editorConfig,
            isCollaborative: options.collaborative,
            collaborativeTrigger: options.collaborative_trigger,
            migrateHTML: "migrateHTML" in options ? Boolean(options.migrateHTML) : true,
            dynamicPlaceholder: options.dynamic_placeholder,
            dynamicPlaceholderModelReferenceField:
                options.dynamic_placeholder_model_reference_field,
            embeddedComponents:
                "embedded_components" in options ? Boolean(options.embedded_components) : true,
            sandboxedPreview: Boolean(options.sandboxedPreview),
            cssReadonlyAssetId: options.cssReadonly,
            codeview: Boolean(odoo.debug && options.codeview),
        };
    },
};

registry.category("fields").add("html", htmlField, { force: true });
