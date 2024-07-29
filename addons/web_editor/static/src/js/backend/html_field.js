/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { QWebPlugin } from '@web_editor/js/backend/QWebPlugin';
import { TranslationButton } from "@web/views/fields/translation_button";
import { useDynamicPlaceholder } from "@web/views/fields/dynamic_placeholder_hook";
import {
    useBus,
    useService,
    useSpellCheck,
} from "@web/core/utils/hooks";
import {
    getAdjacentPreviousSiblings,
    getAdjacentNextSiblings,
    getRangePosition
} from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { toInline } from '@web_editor/js/backend/convert_inline';
import { getBundle, loadBundle } from '@web/core/assets';
import {
    Component,
    useRef,
    useState,
    onWillStart,
    onMounted,
    onWillUpdateProps,
    useEffect,
    onWillUnmount,
    status,
} from "@odoo/owl";
import { uniqueId } from '@web/core/utils/functions';
// Ensure `@web/views/fields/html/html_field` is loaded first as this module
// must override the html field in the registry.
import '@web/views/fields/html/html_field';

let stripHistoryIds;

export class HtmlField extends Component {
    static template = "web_editor.HtmlField";
    static components = {
        TranslationButton,
    };
    static defaultProps = { dynamicPlaceholder: false };
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        codeview: { type: Boolean, optional: true },
        isCollaborative: { type: Boolean, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true, default: false },
        dynamicPlaceholderModelReferenceField: { type: String, optional: true },
        cssReadonlyAssetId: { type: String, optional: true },
        isInlineStyle: { type: Boolean, optional: true },
        sandboxedPreview: {type: Boolean, optional: true},
        wrapper: { type: String, optional: true },
        wysiwygOptions: { type: Object },
        hasReadonlyModifiers: { type: Boolean, optional: true },
    };

    setup() {
        this.containsComplexHTML = this.computeContainsComplexHTML();
        this.sandboxedPreview = this.props.sandboxedPreview || this.containsComplexHTML;

        this.readonlyElementRef = useRef("readonlyElement");
        this.codeViewRef = useRef("codeView");
        this.iframeRef = useRef("iframe");
        this.codeViewButtonRef = useRef("codeViewButton");

        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder();
        }
        this.rpc = useService("rpc");

        this.onIframeUpdated = this.env.onIframeUpdated || (() => {});

        this.state = useState({
            showCodeView: false,
            iframeVisible: false,
        });

        const { model } = this.props.record;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () =>
            this.commitChanges({ urgent: true })
        );
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges({ shouldInline: true }))
        );

        useSpellCheck();

        this._onUpdateIframeId = "onLoad_" + uniqueId("FieldHtml");

        onWillStart(async () => {
            if (this.props.cssReadonlyAssetId) {
                this.cssReadonlyAsset = await getBundle(this.props.cssReadonlyAssetId);
            }
            await this._lazyloadWysiwyg();
        });
        this._lastRecordInfo = {
            res_model: this.props.record.resModel,
            res_id: this.props.record.resId,
        };
        onWillUpdateProps((newProps) => {
            if (!newProps.readonly && !this.sandboxedPreview && this.state.iframeVisible) {
                this.state.iframeVisible = false;
            }

            const newRecordInfo = {
                res_model: newProps.record.resModel,
                res_id: newProps.record.resId,
            };
            if (JSON.stringify(this._lastRecordInfo) !== JSON.stringify(newRecordInfo)) {
                this.currentEditingValue = undefined;
            }
            this._lastRecordInfo = newRecordInfo;
        });
        useEffect(() => {
            (async () => {
                if (this._qwebPlugin) {
                    this._qwebPlugin.destroy();
                }
                if (this.props.readonly || (!this.state.showCodeView && this.sandboxedPreview)) {
                    if (this.showIframe) {
                        await this._setupReadonlyIframe();
                    } else if (this.readonlyElementRef.el) {
                        this._qwebPlugin = new QWebPlugin();
                        this._qwebPlugin.sanitizeElement(this.readonlyElementRef.el);
                        // Ensure all external links are opened in a new tab.
                        retargetLinks(this.readonlyElementRef.el);

                        const hasReadonlyModifiers = this.props.hasReadonlyModifiers;
                        if (!hasReadonlyModifiers) {
                            const $el = $(this.readonlyElementRef.el);
                            $el.off('.checklistBinding');
                            $el.on('click.checklistBinding', 'ul.o_checklist > li', this._onReadonlyClickChecklist.bind(this));
                            $el.on('click.checklistBinding', '.o_stars .fa-star, .o_stars .fa-star-o', this._onReadonlyClickStar.bind(this));
                        }
                    }
                } else {
                    const codeViewEl = this._getCodeViewEl();
                    if (codeViewEl) {
                        codeViewEl.value = this.props.record.data[this.props.name];
                    }
                }
            })();
        });
        onMounted(() => {
            this.dynamicPlaceholder?.setElementRef(this.wysiwyg);
        });
        onWillUnmount(async () => {
            if (!this.props.readonly && this._isDirty()) {
                // If we still have uncommited changes, commit them to avoid losing them.
                await this.commitChanges();
            }
            if (this._qwebPlugin) {
                this._qwebPlugin.destroy();
            }
            if (this.resizerHandleObserver) {
                this.resizerHandleObserver.disconnect();
            }
        });
    }

    /**
     * Check whether the current value contains nodes that would break
     * on insertion inside an existing body.
     *
     * @returns {boolean} true if 'this.props.value' contains a node
     * that can only exist once per document.
     */
    computeContainsComplexHTML() {
        const domParser = new DOMParser();
        const parsedOriginal = domParser.parseFromString(this.props.record.data[this.props.name] || '', 'text/html');
        return !!parsedOriginal.head.innerHTML.trim();
    }

    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }
    get markupValue () {
        return this.props.record.data[this.props.name];
    }
    get showIframe () {
        return (this.sandboxedPreview && !this.state.showCodeView) || (this.props.readonly && this.props.cssReadonlyAssetId);
    }
    get wysiwygOptions() {
        let dynamicPlaceholderOptions = {};
        if (this.props.dynamicPlaceholder) {
            dynamicPlaceholderOptions = {
                // Add the powerbox option to open the Dynamic Placeholder
                // generator.
                powerboxCommands: [
                    {
                        category: _t('Marketing Tools'),
                        name: _t('Dynamic Placeholder'),
                        priority: 10,
                        description: _t('Insert personalized content'),
                        fontawesome: 'fa-magic',
                        callback: () => {
                            this.wysiwygRangePosition = getRangePosition(document.createElement('x'), this.wysiwyg.options.document || document);
                            this.dynamicPlaceholder.updateModel(this.props.dynamicPlaceholderModelReferenceField);
                            // The method openDynamicPlaceholder need to be triggered
                            // after the focus from powerBox prevalidate.
                            setTimeout(async () => {
                                await this.dynamicPlaceholder.open(
                                    {
                                        validateCallback: this.onDynamicPlaceholderValidate.bind(this),
                                        closeCallback: this.onDynamicPlaceholderClose.bind(this),
                                        positionCallback: this.positionDynamicPlaceholder.bind(this),
                                    }
                                );
                            });
                        },
                    }
                ],
                powerboxFilters: [this._filterPowerBoxCommands.bind(this)],
            }
        }

        const wysiwygOptions = {...this.props.wysiwygOptions};
        const { sanitize_tags, sanitize } = this.props.record.fields[this.props.name];
        if (sanitize_tags || (sanitize_tags === undefined && sanitize)) {
            wysiwygOptions.allowCommandVideo = false; // Tag-sanitized fields remove videos.
        }

        return {
            value: this.props.record.data[this.props.name],
            autostart: false,
            onAttachmentChange: this._onAttachmentChange.bind(this),
            onDblClickEditableMedia: this._onDblClickEditableMedia.bind(this),
            onWysiwygBlur: this._onWysiwygBlur.bind(this),
            ...wysiwygOptions,
            ...dynamicPlaceholderOptions,
            recordInfo: {
                res_model: this.props.record.resModel,
                res_id: this.props.record.resId,
            },
            collaborationChannel: this.props.isCollaborative && {
                collaborationModelName: this.props.record.resModel,
                collaborationFieldName: this.props.name,
                collaborationResId: parseInt(this.props.record.resId),
            },
            fieldId: this.props.id,
            editorPlugins: [...(wysiwygOptions.editorPlugins || []), QWebPlugin, this.MoveNodePlugin],
            record: this.props.record,
        };
    }
    /**
     * Prevent usage of the dynamic placeholder command inside widgets
     * containing background images ( cover & masonry ).
     *
     * We cannot use dynamic placeholder in block containing background images
     * because the email processing will flatten the text into the background
     * image and this case the dynamic placeholder cannot be dynamic anymore.
     *
     * @param {Array} commands commands available in this wysiwyg
     * @returns {Array} commands which can be used after the filter was applied
     */
    _filterPowerBoxCommands(commands) {
        let selectionIsInForbidenSnippet = false;
        if (this.wysiwyg && this.wysiwyg.odooEditor) {
            const selection = this.wysiwyg.odooEditor.document.getSelection();
            selectionIsInForbidenSnippet = this.wysiwyg.closestElement(
                selection.anchorNode,
                'div[data-snippet="s_cover"], div[data-snippet="s_masonry_block"]'
            );
        }
        return selectionIsInForbidenSnippet ? commands.filter((o) => o.title !== "Dynamic Placeholder") : commands;
    }

    getEditingValue () {
        const codeViewEl = this._getCodeViewEl();
        if (codeViewEl) {
            return codeViewEl.value;
        } else {
            if (this.wysiwyg) {
                return this.wysiwyg.getValue();
            } else {
                return null;
            }
        }
    }
    async updateValue() {
        const value = this.getEditingValue();
        const lastValue = (this.props.record.data[this.props.name] || "").toString();
        if (
            value !== null &&
            !(!lastValue && stripHistoryIds(value) === "<p><br></p>") &&
            stripHistoryIds(value) !== stripHistoryIds(lastValue)
        ) {
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", false);
            this.currentEditingValue = value;
            await this.props.record.update({ [this.props.name]: value });
        }
    }
    async startWysiwyg(wysiwyg) {
        this.wysiwyg = wysiwyg;
        await this.wysiwyg.startEdition();
        wysiwyg.$editable[0].classList.add("odoo-editor-qweb");

        if (this.props.codeview) {
            const $codeviewButtonToolbar = $(`
                <div id="codeview-btn-group" class="btn-group">
                    <button class="o_codeview_btn btn btn-primary">
                        <i class="fa fa-code"></i>
                    </button>
                </div>
            `);
            this.wysiwyg.toolbarEl.append($codeviewButtonToolbar[0]);
            $codeviewButtonToolbar.click(this.toggleCodeView.bind(this));
        }
        this.wysiwyg.odooEditor.addEventListener("historyStep", () =>
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", this._isDirty())
        );

        if (this.props.isCollaborative) {
            this.wysiwyg.odooEditor.addEventListener("onExternalHistorySteps", () =>
                this.props.record.model.bus.trigger("FIELD_IS_DIRTY", this._isDirty())
            );
        }

        this.isRendered = true;
    }
    /**
     * Toggle the code view and update the UI.
     */
    toggleCodeView() {
        this.state.showCodeView = !this.state.showCodeView;

        if (this.wysiwyg) {
            this.wysiwyg.odooEditor.observerUnactive('toggleCodeView');
            if (this.state.showCodeView) {
                this.wysiwyg.$editable.remove();
                this.wysiwyg.odooEditor.toolbarHide();
                const value = this.wysiwyg.getValue();
                this.props.record.update({ [this.props.name]: value });
            } else {
                this.wysiwyg.odooEditor.observerActive('toggleCodeView');
            }
        }
        if (!this.state.showCodeView) {
            const $codeview = $(this.codeViewRef.el);
            const value = $codeview.val();
            this.props.record.update({ [this.props.name]: value });

        }
    }
    onDynamicPlaceholderValidate(chain, defaultValue) {
        if (chain) {
            // Ensure the focus is in the editable document
            // before inserting the <t> element.
            this.wysiwyg.focus();
            let dynamicPlaceholder = "object." + chain;
            dynamicPlaceholder += defaultValue && defaultValue !== '' ? ` or '''${defaultValue}'''` : '';
            const t = document.createElement('T');
            t.setAttribute('t-out', dynamicPlaceholder);
            this.wysiwyg.odooEditor.execCommand('insert', t);
            // Ensure the dynamic placeholder <t> element is sanitized.
            this.wysiwyg.odooEditor.sanitize(t);
        }
    }
    onDynamicPlaceholderClose() {
        this.wysiwyg.focus();
    }

    /**
     * @param {HTMLElement} popover
     * @param {Object} position
     */
    positionDynamicPlaceholder(popover, position) {
        // make sure the popover won't be out(below) of the page
        const enoughSpaceBelow = window.innerHeight - popover.clientHeight - this.wysiwygRangePosition.top;
        let topPosition = (enoughSpaceBelow > 0) ? this.wysiwygRangePosition.top : this.wysiwygRangePosition.top + enoughSpaceBelow;

        // Offset the popover to ensure the arrow is pointing at
        // the precise range location.
        let leftPosition = this.wysiwygRangePosition.left - 14;
        // make sure the popover won't be out(right) of the page
        const enoughSpaceRight = window.innerWidth - popover.clientWidth - leftPosition;
        leftPosition = (enoughSpaceRight > 0) ? leftPosition : leftPosition + enoughSpaceRight;

        // Apply the position back to the element.
        popover.style.top = topPosition + 'px';
        popover.style.left = leftPosition + 'px';
    }
    async commitChanges({ urgent, shouldInline } = {}) {
        if (this._isDirty() || urgent || (shouldInline && this.props.isInlineStyle)) {
            let savePendingImagesPromise, toInlinePromise;
            if (this.wysiwyg && this.wysiwyg.odooEditor) {
                this.wysiwyg.odooEditor.observerUnactive('commitChanges');
                savePendingImagesPromise = this.wysiwyg.savePendingImages();
                if (this.props.isInlineStyle) {
                    // Avoid listening to changes made during the _toInline process.
                    toInlinePromise = this._toInline();
                }
                if (urgent && status(this) !== 'destroyed') {
                    await this.updateValue();
                }
                await savePendingImagesPromise;
                if (this.props.isInlineStyle) {
                    await toInlinePromise;
                }
                this.wysiwyg.odooEditor.observerActive('commitChanges');
            }
            if (status(this) !== 'destroyed') {
                await this.updateValue();
            }
        }
    }
    async _lazyloadWysiwyg() {
        // In some bundle (eg. `web.qunit_suite_tests`), the following module is already included.
        let wysiwygModule = await odoo.loader.modules.get('@web_editor/js/wysiwyg/wysiwyg');
        this.MoveNodePlugin = (await odoo.loader.modules.get('@web_editor/js/wysiwyg/MoveNodePlugin'))?.MoveNodePlugin;
        // Otherwise, load the module.
        if (!wysiwygModule) {
            await loadBundle('web_editor.backend_assets_wysiwyg');
            wysiwygModule = await odoo.loader.modules.get('@web_editor/js/wysiwyg/wysiwyg');
            this.MoveNodePlugin = (await odoo.loader.modules.get('@web_editor/js/wysiwyg/MoveNodePlugin')).MoveNodePlugin;
        }
        stripHistoryIds = wysiwygModule.stripHistoryIds;
        this.Wysiwyg = wysiwygModule.Wysiwyg;
    }
    _isDirty() {
        const strippedPropValue = stripHistoryIds(String(this.props.record.data[this.props.name]));
        const strippedEditingValue = stripHistoryIds(this.getEditingValue());
        const domParser = new DOMParser();
        const codeViewEl = this._getCodeViewEl();
        let parsedPreviousValue;
        // If the wysiwyg is active, we need to clean the content of the
        // initialValue as the editingValue will be cleaned.
        if (!codeViewEl && this.wysiwyg) {
            const editable = domParser.parseFromString(strippedPropValue || '<p><br></p>', 'text/html').body;
            // Temporarily append the editable to the DOM because the
            // wysiwyg.getValue can indirectly call methods that needs to have
            // access the node.ownerDocument.defaultView.getComputedStyle.
            // By appending the editable to the dom, the node.ownerDocument will
            // have a `defaultView`.
            const div = document.createElement('div');
            div.style.display = 'none';
            div.append(editable);
            document.body.append(div);
            const editableValue = stripHistoryIds(this.wysiwyg.getValue({ $layout: $(editable) }));
            div.remove();
            parsedPreviousValue = domParser.parseFromString(editableValue, 'text/html').body;
        } else {
            parsedPreviousValue = domParser.parseFromString(strippedPropValue || '<p><br></p>', 'text/html').body;
        }
        const parsedNewValue = domParser.parseFromString(strippedEditingValue, 'text/html').body;
        return !this.props.readonly && parsedPreviousValue.innerHTML !== parsedNewValue.innerHTML;
    }
    _getCodeViewEl() {
        return this.state.showCodeView && this.codeViewRef.el;
    }
    async _setupReadonlyIframe() {
        const iframeTarget = this.sandboxedPreview
            ? this.iframeRef.el.contentDocument.documentElement
            : this.iframeRef.el.contentDocument.querySelector('#iframe_target');

        if (this.iframePromise && iframeTarget) {
            if (iframeTarget.innerHTML !== this.props.record.data[this.props.name]) {
                iframeTarget.innerHTML = this.props.record.data[this.props.name];
                retargetLinks(iframeTarget);
            }
            return this.iframePromise;
        }
        this.iframePromise = new Promise((resolve) => {
            let value = this.props.record.data[this.props.name];

            // this bug only appears on some computers with some chrome version.
            let avoidDoubleLoad = 0;

            // inject content in iframe
            window.top[this._onUpdateIframeId] = (_avoidDoubleLoad) => {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                resolve();
                this.state.iframeVisible = true;
                this.onIframeUpdated();
            };

            this.iframeRef.el.addEventListener('load', async () => {
                const _avoidDoubleLoad = ++avoidDoubleLoad;

                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg immediate iframe double load detected');
                    return;
                }
                const cwindow = this.iframeRef.el.contentWindow;
                try {
                    cwindow.document;
                } catch {
                    return;
                }
                if (!this.sandboxedPreview) {
                    cwindow.document
                        .open("text/html", "replace")
                        .write(
                            '<!DOCTYPE html><html>' +
                            '<head>' +
                                '<meta charset="utf-8"/>' +
                                '<meta http-equiv="X-UA-Compatible" content="IE=edge"/>\n' +
                                '<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>\n' +
                            '</head>\n' +
                            '<body class="o_in_iframe o_readonly" style="overflow: hidden;">\n' +
                                '<div id="iframe_target"></div>\n' +
                            '</body>' +
                            '</html>');
                }
                if (this.props.cssReadonlyAssetId) {
                    for (const cssLib of this.cssReadonlyAsset.cssLibs) {
                        const link = cwindow.document.createElement('link');
                        link.setAttribute('type', 'text/css');
                        link.setAttribute('rel', 'stylesheet');
                        link.setAttribute('href', cssLib);
                        cwindow.document.head.append(link);
                    }
                    for (const cssContent of this.cssReadonlyAsset.cssContents) {
                        const style = cwindow.document.createElement('style');
                        style.setAttribute('type', 'text/css');
                        const textNode = cwindow.document.createTextNode(cssContent);
                        style.append(textNode);
                        cwindow.document.head.append(style);
                    }
                }

                if (!this.sandboxedPreview) {
                    const iframeTarget = cwindow.document.querySelector('#iframe_target');
                    iframeTarget.innerHTML = value;

                    const script = cwindow.document.createElement('script');
                    script.setAttribute('type', 'text/javascript');
                    const scriptTextNode = document.createTextNode(
                        `if (window.top.${this._onUpdateIframeId}) {` +
                            `window.top.${this._onUpdateIframeId}(${_avoidDoubleLoad})` +
                        `}`
                    );
                    script.append(scriptTextNode);
                    cwindow.document.body.append(script);
                } else {
                    cwindow.document.documentElement.innerHTML = value;
                }

                const height = cwindow.document.body.scrollHeight;
                this.iframeRef.el.style.height = Math.max(30, Math.min(height, 500)) + 'px';

                retargetLinks(cwindow.document.body);
                if (this.sandboxedPreview) {
                    this.state.iframeVisible = true;
                    this.onIframeUpdated();
                    resolve();
                }
            });
            // Force the iframe to call the `load` event. Without this line, the
            // event 'load' might never trigger.
            this.iframeRef.el.after(this.iframeRef.el);

        });
        return this.iframePromise;
    }
    /**
     * Converts CSS dependencies to CSS-independent HTML.
     * - CSS display for attachment link -> real image
     * - Font icons -> images
     * - CSS styles -> inline styles
     *
     * @private
     */
    async _toInline() {
        const $editable = this.wysiwyg.getEditable();
        this.wysiwyg.odooEditor.sanitize(this.wysiwyg.odooEditor.editable);
        const html = this.wysiwyg.getValue();
        const $odooEditor = $editable.closest('.odoo-editor-editable');
        // Save correct nodes references.
        // Remove temporarily the class so that css editing will not be converted.
        $odooEditor.removeClass('odoo-editor-editable');
        $editable.html(html);

        await toInline($editable, undefined, this.wysiwyg.$iframe);
        $odooEditor.addClass('odoo-editor-editable');

        this.wysiwyg.setValue($editable.html());
        this.wysiwyg.odooEditor.sanitize(this.wysiwyg.odooEditor.editable);
    }
    _onAttachmentChange(attachment) {
        // This only needs to happen for the composer for now
        if (!(this.props.record.fieldNames.includes('attachment_ids') && this.props.record.resModel === 'mail.compose.message')) {
            return;
        }
        this.props.record.data.attachment_ids.linkTo(attachment.id, attachment);
    }
    _onDblClickEditableMedia(ev) {
        const el = ev.currentTarget;
        if (el.nodeName === 'IMG' && el.src) {
            this.wysiwyg.showImageFullscreen(el.src);
        }
    }
    _onWysiwygBlur() {
        // Avoid save on blur if the html field is in inline mode.
        if (this.props.isInlineStyle) {
            this.updateValue();
        } else {
            this.commitChanges();
        }
    }
    async _onReadonlyClickChecklist(ev) {
        if (ev.offsetX > 0) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        const checked = $(ev.target).hasClass('o_checked');
        let checklistId = $(ev.target).attr('id');
        checklistId = checklistId && checklistId.replace('checkId-', '');
        checklistId = parseInt(checklistId || '0');

        const value = await this.rpc('/web_editor/checklist', {
            res_model: this.props.record.resModel,
            res_id: this.props.record.resId,
            filename: this.props.name,
            checklistId: checklistId,
            checked: !checked,
        });
        if (value) {
            this.props.record.update({ [this.props.name]: value });
        }
    }
    async _onReadonlyClickStar(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const node = ev.target;
        const previousStars = getAdjacentPreviousSiblings(node, sib => (
            sib.nodeType === Node.ELEMENT_NODE && sib.className.includes('fa-star')
        ));
        const nextStars = getAdjacentNextSiblings(node, sib => (
            sib.nodeType === Node.ELEMENT_NODE && sib.classList.contains('fa-star')
        ));
        const shouldToggleOff = node.classList.contains('fa-star') && !nextStars.length;
        const rating = shouldToggleOff ? 0 : previousStars.length + 1;

        let starsId = $(node).parent().attr('id');
        starsId = starsId && starsId.replace('checkId-', '');
        starsId = parseInt(starsId || '0');
        const value = await this.rpc('/web_editor/stars', {
            res_model: this.props.record.resModel,
            res_id: this.props.record.resId,
            filename: this.props.name,
            starsId,
            rating,
        });
        if (value) {
            this.props.record.update({ [this.props.name]: value });
        }
    }
}

export const htmlField = {
    component: HtmlField,
    displayName: _t("Html"),
    supportedOptions: [{
        label: _t("CSS Edit"),
        name: "cssEdit",
        type: "string"
    }, {
        label: _t("Height"),
        name: "height",
        type: "string"
    }, {
        label: _t("Min height"),
        name: "minHeight",
        type: "string"
    }, {
        label: _t("Max height"),
        name: "maxHeight",
        type: "string"
    }, {
        label: _t("Snippets"),
        name: "snippets",
        type: "string"
    }, {
        label: _t("No videos"),
        name: "noVideos",
        type: "boolean",
        default: true
    }, {
        label: _t("Resizable"),
        name: "resizable",
        type: "boolean",
    }, {
        label: _t("Sandboxed preview"),
        name: "sandboxedPreview",
        type: "boolean",
        help: _t("With the option enabled, all content can only be viewed in a sandboxed iframe or in the code editor."),
    }, {
        label: _t("Collaborative edition"),
        name: "collaborative",
        type: "boolean",
    },{
        label: _t("Collaborative trigger"),
        name: "collaborative_trigger",
        type: "selection",
        choices: [
            { label: _t("Focus"), value: "focus" },
            { label: _t("Start"), value: "start" },
        ],
        default: "focus",
        help: _t("Specify when the collaboration starts. 'Focus' will start the collaboration session when the user clicks inside the text field (default), 'Start' when the record is loaded (could impact performance if set)."),
    }, {
        label: _t("Codeview"),
        name: "codeview",
        type: "boolean",
        help: _t("Allow users to view and edit the field in HTML.")
    }],
    supportedTypes: ["html"],
    extractProps({ attrs, options }, dynamicInfo) {
        const wysiwygOptions = {
            placeholder: attrs.placeholder,
            noAttachment: options['no-attachment'],
            inIframe: Boolean(options.cssEdit),
            iframeCssAssets: options.cssEdit,
            iframeHtmlClass: attrs.iframeHtmlClass,
            snippets: options.snippets,
            mediaModalParams: {
                noVideos: 'noVideos' in options ? options.noVideos : true,
                useMediaLibrary: true,
            },
            linkOptions: {
                forceNewWindow: true,
            },
            tabsize: 0,
            height: options.height,
            minHeight: options.minHeight,
            maxHeight: options.maxHeight,
            resizable: 'resizable' in options ? options.resizable : false,
        };
        if ('collaborative' in options) {
            wysiwygOptions.collaborative = options.collaborative;
            // Two supported triggers:
            // 'start': Join the peerToPeer connection immediately
            // 'focus': Join when the editable has focus
            wysiwygOptions.collaborativeTrigger = options.collaborative_trigger || 'focus';
        }
	    if ('style-inline' in options) {
	        wysiwygOptions.inlineStyle = Boolean(options['style-inline']);
	    }
        if ('allowCommandImage' in options) {
            // Set the option only if it is explicitly set in the view so a default
            // can be set elsewhere otherwise.
            wysiwygOptions.allowCommandImage = Boolean(options.allowCommandImage);
        }
        if ('allowCommandVideo' in options) {
            // Set the option only if it is explicitly set in the view so a default
            // can be set elsewhere otherwise.
            wysiwygOptions.allowCommandVideo = Boolean(options.allowCommandVideo);
        }
        return {
            codeview: Boolean(odoo.debug && options.codeview),
            placeholder: attrs.placeholder,
            sandboxedPreview: Boolean(options.sandboxedPreview),

            isCollaborative: options.collaborative,
            cssReadonlyAssetId: options.cssReadonly,
            dynamicPlaceholder: options?.dynamic_placeholder || false,
            dynamicPlaceholderModelReferenceField: options?.dynamic_placeholder_model_reference_field || "",
            isInlineStyle: options['style-inline'],

            wysiwygOptions,
            hasReadonlyModifiers: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("html", htmlField, { force: true });

// Ensure all links are opened in a new tab.
const retargetLinks = (container) => {
    for (const link of container.querySelectorAll('a')) {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noreferrer');
    }
}
