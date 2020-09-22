odoo.define('web_editor.wysiwyg', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var JWEditorLib = require('web_editor.jabberwock');
var SnippetsMenu = require('web_editor.snippet.editor').SnippetsMenu;
var weWidgets = require('wysiwyg.widgets');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
var AttributeTranslateDialog = require('web_editor.wysiwyg.translate_attributes');
var config = require('web.config');

var core = require('web.core');
var _t = core._t;

const faZoomClassRegex = RegExp('fa-[0-9]x');

var Wysiwyg = Widget.extend({
    defaultOptions: {
        'recordInfo': {
            'context': {},
        },
    },

    /**
     * @options {Object} options
     * @options {Object} options.recordInfo
     * @options {Object} options.recordInfo.context
     * @options {String} [options.recordInfo.context]
     * @options {integer} [options.recordInfo.res_id]
     * @options {String} [options.recordInfo.data_res_model]
     * @options {integer} [options.recordInfo.data_res_id]
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js
     * @options {Object} options.attachments
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js (for attachmentIDs)
     * @options {function} options.generateOptions
     *   called with the summernote configuration object used before sending to summernote
     *   @see _editorOptions
     **/
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.value = options.value || '';
        this.options = options;
        this.colorPickers = [];
        this.JWEditorLib = JWEditorLib;
        if (this.options.enableTranslation) {
            this._modeConfig = {
                id: 'translate',
                rules: [
                    {
                        selector: [],
                        properties: {
                            editable: {
                                value: false,
                                cascading: true,
                            },
                        },
                    },
                    {
                        selector: [this.JWEditorLib.ContainerNode],
                        properties: {
                            breakable: { value: false },
                        },
                    },
                    {
                        selector: [node => !!node.modifiers.find(this.JWEditorLib.OdooTranslationFormat)],
                        properties: {
                            editable: {
                                value: true,
                                cascading: true,
                            },
                        },
                    },
                    {
                        selector: [node => {
                            const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                            return attributes && attributes.classList.has('o_not_editable');
                        }, () => true],
                        properties: {
                            editable: {
                                value: false,
                                cascading: true,
                            },
                        },
                    },
                ],
            };
        } else if (this.options.enableWebsite) {
            this._modeConfig = {
                id: 'edit',
                rules: [
                    {
                        selector: [
                            (node) => {
                                const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                                const isWrapper = attributes && attributes.classList.has('oe_structure') ;
                                return isWrapper;
                            },
                        ],
                        properties: {
                            breakable: { value: false },
                            allowEmpty: { value: true },
                        },
                    },
                    {
                        selector: [this.JWEditorLib.DividerNode],
                        properties: {
                            breakable: { value: false },
                            allowEmpty: { value: false },
                        },
                    },
                    {
                        selector: [
                            (node) => {
                                const attributes = node.modifiers.find(this.JWEditorLib.Attributes);

                                const isCountdown = attributes && attributes.classList.has('s_countdown');
                                const isNewsletterPopup = attributes && attributes.classList.has('o_newsletter_popup');
                                const isPopup = attributes && attributes.classList.has('s_popup');

                                return isCountdown || isPopup || isNewsletterPopup;
                            },
                            this.JWEditorLib.ContainerNode],
                        properties: {
                            allowEmpty: { value: true },
                        },
                    },
                    {
                        selector: [this.JWEditorLib.OdooFieldNode],
                        properties: {
                            allowEmpty: { value: true },
                        },
                    },
                    {
                        selector: [
                            (node) => {
                                const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                                return attributes && attributes.classList.has('o_header_standard');
                            },
                        ],
                        properties: {
                            editable: {
                                value: false,
                                cascading: true,
                            },
                        },
                    },
                    {
                        selector: [
                            (node) => {
                                const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                                return attributes && attributes.classList.has('o_header_standard');
                            },
                            (node) => {
                                const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                                const linkFormat = node.modifiers.find(this.JWEditorLib.LinkFormat);
                                const linkAttributes = linkFormat && linkFormat.modifiers.find(this.JWEditorLib.Attributes);

                                const hasNavLink = linkAttributes && (linkAttributes.classList.has('nav-link'));
                                const hasContainer = attributes && attributes.classList.has('container');

                                return hasNavLink || hasContainer;
                            },
                        ],
                        properties: {
                            editable: {
                                value: true,
                                cascading: true,
                            },
                        },
                    },
                ],
            };
        }
    },
    /**
     * Load assets and color picker template then call summernote API
     * and replace $el by the summernote editable node.
     *
     * @override
     **/
    willStart: async function () {
        this.$target = this.$el;
        return this._super();
    },
    /**
     *
     * @override
     */
    start: async function () {
        const self = this;
        const _super = this._super;

        if (this.options.enableWebsite) {
            $(document.body).addClass('o_connected_user editor_enable');
        }

        const $mainSidebar = $('<div class="o_main_sidebar">');
        const $snippetManipulators = $('<div id="oe_manipulators" />');

        const customCommands = {
            openMedia: { handler: this.openMediaDialog.bind(this) },
            openTextColorPicker: { handler: this.toggleTextColorPicker.bind(this) },
            openBackgroundColorPicker: { handler: this.toggleBackgroundColorPicker.bind(this) },
            openLinkDialog: { handler: this.openLinkDialog.bind(this) },
            discardOdoo: { handler: this.discardEditions.bind(this) },
            saveOdoo: { handler: this.saveContent.bind(this) },
            cropImage: { handler: this.cropImage.bind(this) },
            transformImage: { handler: this.transformImage.bind(this) },
            describeImage: { handler: this.describeImage.bind(this) },
        };
        this.editor = new JWEditorLib.OdooWebsiteEditor(Object.assign({}, this.options, {
            snippetMenuElement: $mainSidebar[0],
            snippetManipulators: $snippetManipulators[0],
            customCommands: Object.assign(customCommands, this.options.customCommands),
            plugins: this.options.enableWebsite ? [[this.JWEditorLib.OdooField]] : [],
            source: this.value,
            location: this.options.location || [this.el, 'replace'],
            mode: this._modeConfig,
        }));

        if (Array.isArray(odoo.debug) && config.isDebug('assets') && JWEditorLib.DevTools) {
            this.editor.load(JWEditorLib.DevTools);
        }
        await this.editor.start();
        this._bindAfterStart();

        this.$toolbar = $('jw-toolbar').detach();

        this.editorHelpers = this.editor.plugins.get(JWEditorLib.DomHelpers);
        const domLayout = this.editor.plugins.get(JWEditorLib.Layout).engines.dom;
        this.zoneMain = domLayout.root.firstDescendant(node => node.managedZones && node.managedZones.includes('main'));
        this.editorEditable = this.editorHelpers.getDomNodes(this.zoneMain)[0] || this.editorHelpers.getDomNodes(this.zoneMain.parent)[0];

        if (this.options.enableWebsite) {
            const $wrapwrap = $('#wrapwrap');
            $wrapwrap.removeClass('o_editable'); // clean the dom before edition
            this._getEditable($wrapwrap).addClass('o_editable');
            $wrapwrap.data('wysiwyg', this);

            // add class when page content is empty to show the "DRAG BUILDING BLOCKS HERE" block
            const $targetNode = $(this.editorEditable).find(".oe_structure");
            if ($targetNode.length) {
                $targetNode.attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            }
        }

        if (this.options.enableTranslation) {
            this._setupTranslation();
        }

        if (this.options.snippets) {
            document.body.classList.add('editor_has_snippets');
            this.$webEditorToolbar = $('<div id="web_editor-toolbars">');

            var $toolbarHandler = $('#web_editor-top-edit');
            $toolbarHandler.append(this.$webEditorToolbar);

            this.snippetsMenu = new SnippetsMenu(this, Object.assign({
                $el: $(this.editorEditable),
                snippets: this.options.snippets,
                selectorEditableArea: '.o_editable',
                $snippetEditorArea: $snippetManipulators,
                wysiwyg: this,
                JWEditorLib: JWEditorLib,
                onlyStyleTab: this.options.enableTranslation,
            }, this.options));
            await this.snippetsMenu.appendTo($mainSidebar);

            this.$el.on('content_changed', function (e) {
                self.trigger_up('wysiwyg_change');
            });

            const onCommitCheckSnippets = (params) => {
                if (params.commandNames.includes('undo') || params.commandNames.includes('redo')) {
                    setTimeout(() => {
                        // use setTimeout to reload snippets after the redraw
                        this.snippetsMenu.trigger('reload_snippet_dropzones');
                    });
                }
            };
            this.editor.dispatcher.registerCommandHook('@commit', onCommitCheckSnippets);

        } else {
            return _super.apply(this, arguments);
        }
    },

    openLinkDialog() {
        const range = this.editor.selection.range;
        const Link = JWEditorLib.Link;

        let targetedLeaves = [];
        const previousNode = range.start.previousSibling();
        const nextNode = range.start.nextSibling();
        const node = previousNode && Link.isLink(previousNode) ? previousNode : nextNode;
        let currentLink;
        if (!node || !Link.isLink(node)) {
            if (range.isCollapsed()) {
                targetedLeaves = range.targetedNodes();
            } else {
                targetedLeaves = range.selectedNodes();
                targetedLeaves = targetedLeaves.filter(node => !targetedLeaves.includes(node.parent));
            }
        } else {
            currentLink = node.modifiers.find(JWEditorLib.LinkFormat);
            const sameLink = Link.isLink.bind(Link, currentLink);
            targetedLeaves = node.adjacents(sameLink);
        }
        const text = targetedLeaves.map(x => x.textContent).join('');
        const modifiers = range.modifiers;
        const linkFormat = modifiers && modifiers.find(JWEditorLib.LinkFormat);
        const linkFormatAttributes = linkFormat && linkFormat.modifiers.find(JWEditorLib.Attributes);
        let classes = '';
        if (currentLink) {
            const linkAttributes = currentLink.modifiers.find(JWEditorLib.Attributes);
            classes = (linkAttributes && linkAttributes.get('class')) || '';
        }
        const linkDialog = new weWidgets.LinkDialog(this,
            {
                props: {
                    text: text,
                    url: linkFormat && linkFormat.url || '',
                    initialClassNames: classes,
                    target: linkFormatAttributes && linkFormatAttributes.get('target'),
                }
            },
        );
        linkDialog.open();
        linkDialog.on('save', this, async (params)=> {
            const onSaveLinkDialog = async (context) => {
                for (const targetedLeaf of targetedLeaves) {
                    if (targetedLeaf instanceof JWEditorLib.InlineNode) {
                        targetedLeaf.remove();
                    }
                }
                const linkParams = {
                    url: params.url,
                    label: params.text,
                    target: params.isNewWindow ? '_blank' : '',
                };
                const rangeClone = new JWEditorLib.VRange(this.editor, JWEditorLib.VRange.clone(this.editor.selection.range));
                await context.execCommand('link', linkParams);
                const nodes = rangeClone.targetedNodes(JWEditorLib.InlineNode);
                const links = nodes.map(node => node.modifiers.find(JWEditorLib.LinkFormat)).filter(f => f);
                for (const link of links) {
                    link.modifiers.get(JWEditorLib.Attributes).set('class', params.classes);
                }
                rangeClone.remove()
            };
            await this.editor.execCommand(onSaveLinkDialog);
        });
    },
    openMediaDialog(params) {
        const nodes = params.context.range.selectedNodes();
        const node = nodes[0];
        let $fontAwesomeNode;

        if (nodes.length === 1 && node instanceof JWEditorLib.FontAwesomeNode) {
            // TODO: we use previousSibling because getDomNodes return the wrong
            //       node. change the line when the getDomNodes is fixed in
            //       jabberwock.
            const $originalFontAwesome = this.editorHelpers.getDomNodes(node)[0].previousSibling;
            $fontAwesomeNode = $($originalFontAwesome).clone();
            params.htmlClass = [...$fontAwesomeNode[0].classList].filter((className) => {
                return !className.startsWith('fa') || faZoomClassRegex.test(className);
            }).join(' ');
        }

        // avoid circular reference
        delete params.context;

        let mediaDialog = new weWidgets.MediaDialog(this, params, $fontAwesomeNode);
        mediaDialog.open();
        mediaDialog.on('save', this, async (element) => {
            if(params.htmlClass) element.className += " " + params.htmlClass;
            await this.editorHelpers.insertHtml(this.editor, element.outerHTML);
        });
    },
    async saveContent(context = this.editor) {
        if (this.options.enableTranslation) {
            await this._onSaveTranslation(context);
        } else {
            await this.saveToServer(context);
        }
    },
    _setColor(colorpicker, setCommandId, unsetCommandId, color, $dropDownToToggle = undefined) {
        if(color === "") {
            this.editor.execCommand(unsetCommandId);
        } else {
            if (colorpicker.colorNames.indexOf(color) !== -1) {
                // todo : find a better way to detect and send css variable
                color = "var(--" + color + ")";
            }
            this.editor.execCommand(setCommandId, {color: color});
        }
        if($dropDownToToggle !== undefined) {
            $dropDownToToggle.find(".dropdown-toggle").dropdown("toggle");
        }
    },
    async initColorPicker($dropdownNode, setCommandId, unsetCommandId) {
        if (!$dropdownNode.hasClass("colorpicker-initalized")) {
            $dropdownNode.addClass("colorpicker-initalized");
            // Init the colorPalete for this color picker Dropdown.
            const colorpicker = new ColorPaletteWidget(this, {});

            // Prevent the dropdown to be closed when click inside it
            $dropdownNode.on('click', (e)=> {
                e.stopImmediatePropagation();
                e.preventDefault();
            })
            $dropdownNode.find('.dropdown-menu').empty();
            await colorpicker.appendTo($dropdownNode.find('.dropdown-menu'));
            // Events listeners to trigger color changes
            colorpicker.on('custom_color_picked', this, (e) => {
                this._setColor(colorpicker, setCommandId, unsetCommandId, e.data.color);
            });
            colorpicker.on('color_picked', this, (e) => {
                this._setColor(colorpicker, setCommandId, unsetCommandId, e.data.color, $dropdownNode);
            });
        }
    },
    async toggleTextColorPicker() {
        // event.target equal the current toggle button clicked.
        // window.event can be undefined during Qunit test
        const $textColorDropdown = event ? $(event.target).parent() : $(".jw-dropdown-textcolor");
        await this.initColorPicker(
            $textColorDropdown,
            "colorText",
            "uncolorText");

        $textColorDropdown.find(".dropdown-toggle").dropdown("toggle");
    },
    async toggleBackgroundColorPicker() {
        // event.target equal the current toggle button clicked.
        // window.event can be undefined during Qunit test
        const $backgroundColorDropdown = event ? $(event.target).parent() : $(".jw-dropdown-backgroundcolor");
        await this.initColorPicker(
            $backgroundColorDropdown,
            "colorBackground",
            "uncolorBackground");

        $backgroundColorDropdown.find(".dropdown-toggle").dropdown("toggle");
    },

    /**
     * @override
     */
    destroy: function () {
        this.editor.stop();
        this._super();
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Return the editable area.
     *
     * @returns {jQuery}
     */
    getEditable: function () {
        return this.$editor;
    },
    /**
     * Return true if the content has changed.
     *
     * @returns {Boolean}
     */
    isDirty: async function () {
        // todo: use jweditor memory to know if it's dirty.
        return true;
    },
    /**
     * Set the focus on the element.
     */
    focus: function () {
        // todo: handle tab that need to go to next field if the editor does not
        //       catch it.
        this.$el.find('[contenteditable="true"]').focus();
    },
    /**
     * Get the value of the editable element.
     *
     * @param {object} [options]
     * @param {jQueryElement} [options.$layout]
     * @returns {String}
     */
    getValue: async function (format) {
        return this.editor.getValue(format || 'text/html');
    },
    /**
     * @param {String} value
     * @param {Object} options
     * @param {Boolean} [options.notifyChange]
     * @returns {String}
     */
    setValue: function (value, options) {
        this._value = value;
    },
    saveToServer: async function (context = this.editor, reload = true) {
        const defs = [];
        this.trigger_up('edition_will_stopped');
        this.trigger_up('ready_to_save', {defs: defs});
        await Promise.all(defs);

        if (this.snippetsMenu) {
            await this.snippetsMenu.cleanForSave();
        }

        return this._saveWebsiteContent(context)
            .then(() => {
                this.trigger_up('edition_was_stopped');
                if (reload) window.location.reload();
            }).catch(error => {
                console.error('Impossible to save.', error);
            });
    },
    discardEditions: async function () {
        var self = this;
        return new Promise(function (resolve, reject) {
            var confirm = Dialog.confirm(this, _t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."), {
                confirm_callback: resolve,
            });
            confirm.on('closed', self, reject);
        }).then(function () {
            window.onbeforeunload = null;
            window.location.reload();
        });
    },
    cropImage: async function (params) {
        const imageNodes = params.context.range.targetedNodes(JWEditorLib.ImageNode);
        const imageNode = imageNodes.length === 1 && imageNodes[0];
        if (imageNode) {
            const domEngine = this.editor.plugins.get(JWEditorLib.Layout).engines.dom;
            const $node = $(domEngine.getDomNodes(imageNode)[0]);
            $node.off('image_cropped');
            $node.on('image_cropped', () => this._updateAttributes($node[0]));
            new weWidgets.ImageCropWidget(this, $node[0]).appendTo($('#wrap'));
        }
    },
    _updateAttributes(node) {
        const attributes = {}
        for (const attr of node.attributes){
            attributes[attr.name] = attr.value;
        }
        this.editorHelpers.updateAttributes(this.editor, node, attributes);
    },
    transformImage: async function (params) {
        const imageNodes = params.context.range.targetedNodes(JWEditorLib.ImageNode);
        const imageNode = imageNodes.length === 1 && imageNodes[0];
        if (imageNode) {
            const domEngine = this.editor.plugins.get(JWEditorLib.Layout).engines.dom;
            const $node = $(domEngine.getDomNodes(imageNode)[0]);
            this._transform($node);
        }
    },
    _transform($image) {
        if ($image.data('transfo-destroy')) {
            $image.removeData('transfo-destroy');
            return;
        }

        $image.transfo();

        const mouseup = (event) => {
            $('.note-popover button[data-event="transform"]').toggleClass('active', $image.is('[style*="transform"]'));
        };
        $(document).on('mouseup', mouseup);

        const mousedown = (event) => {
            if (!$(event.target).closest('.transfo-container').length) {
                $image.transfo('destroy');
                $(document).off('mousedown', mousedown).off('mouseup', mouseup);
            }
            if ($(event.target).closest('.note-popover').length) {
                $image.data('transfo-destroy', true).attr('style', ($image.attr('style') || '').replace(/[^;]*transform[\w:]*;?/g, ''));
            }
            this._updateAttributes($image[0])
        };
        $(document).on('mousedown', mousedown);
    },
    describeImage: async function (params) {
        const imageNodes = params.context.range.targetedNodes(JWEditorLib.ImageNode);
        const imageNode = imageNodes.length === 1 && imageNodes[0];
        if (imageNode) {
            const domEngine = this.editor.plugins.get(JWEditorLib.Layout).engines.dom;
            const node = domEngine.getDomNodes(imageNode)[0];
            var altDialog = new weWidgets.AltDialog(this, {}, node);
            altDialog.on('save', this, () => this._updateAttributes(node));
            altDialog.open();
        }
    },

    getFormatInfo: function() {
        return this.editor.plugins.get(JWEditorLib.Odoo).formatInfo;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Save after any cleaning has been done and before reloading
     * the page.
     */
    async _saveWebsiteContent(context = this.editor) {
        return new Promise((resolve, reject) => {
            const wysiwygSaveContent = async (context)=> {
                await this._saveModifiedImages(context);
                await this._saveViewBlocks();
                await this._saveCoverPropertiesBlocks(context);
                await this._saveMegaMenuClasses();
            };
            context.execCommand(wysiwygSaveContent).then(params => {
                if (params && params.error) {
                    reject(params.error.message);
                } else {
                    resolve();
                }
            });
        });
    },
    /**
     * Gets jQuery cloned element with internal text nodes escaped for XML
     * storage.
     *
     * @private
     * @param {jQuery} $el
     * @return {jQuery}
     */
    _getEscapedElement: function ($el) {
        var escaped_el = $el.clone();
        var to_escape = escaped_el.find('*').addBack();
        to_escape = to_escape.not(to_escape.filter('object,iframe,script,style,[data-oe-model][data-oe-model!="ir.ui.view"]').find('*').addBack());
        to_escape.contents().each(function () {
            if (this.nodeType === 3) {
                this.nodeValue = $('<div />').text(this.nodeValue).html();
            }
        });
        return escaped_el;
    },
    /**
     * Returns a translation object.
     *
     * @private
     * @param {Node} node
     * @returns {Object}
     */
    _getTranslationObject: function (node) {
        var $node = $(node);
        var id = +$node.data('oe-translation-id');
        if (!id) {
            id = $node.data('oe-model') + ',' + $node.data('oe-id') + ',' + $node.data('oe-field');
        }
        var translation = _.find(this.translations, function (translation) {
            return translation.id === id;
        });
        if (!translation) {
            this.translations.push(translation = {'id': id});
        }
        return translation;
    },
    /**
     * @private
     */
    _markTranslatableNodes: function () {
        const self = this;
        const $editable = $(this.editorEditable);
        $editable.prependEvent('click.translator', function (ev) {
            if (ev.ctrlKey || !$(ev.target).is(':o_editable')) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
        });

        // attributes

        this.$nodesToTranslateAttributes.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node) {
                if (node) {
                    var translation = self._getTranslationObject(node);
                    translation.value = (translation.value ? translation.value : $node.html()).replace(/[ \t\n\r]+/, ' ');
                    $node.attr('data-oe-translation-state', (translation.state || 'to_translate'));
                }
            });
        });

        this.$nodesToTranslateAttributes.prependEvent('mousedown.translator click.translator mouseup.translator', function (ev) {
            if (ev.ctrlKey) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            if (ev.type !== 'mousedown') {
                return;
            }

            new AttributeTranslateDialog(self, {
                editor: self.editor,
                editorHelpers: self.editorHelpers,
            }, ev.target).open();
        });
    },
    /**
     * Return a promise resulting from a rpc to 'ir.ui.view' to save the given
     * view to the given viewId.
     *
     * @param {JQuery} $elem
     * @param {number} viewId
     * @param {string} [xpath]
     */
    _saveViewTo($elem, viewId, xpath = null) {
        const $escapedElement = this._getEscapedElement($elem);
        return this._rpc({
            model: 'ir.ui.view',
            method: 'save',
            args: [
                viewId,
                $escapedElement.prop('outerHTML'),
                xpath,
            ],
            context: this.options.recordInfo.context,
        });
    },
    /**
     * Return a promise resulting from a rpc to 'ir.translation' to save the
     * given view to the given translationId.
     *
     * @param {JQuery} $elem
     * @param {number} translationId
     * @param {string} [xpath]
     */
    _saveTranslationTo($elem, translationId) {
        const $escapedElement = this._getEscapedElement($elem);
        return this._rpc({
            model: 'ir.translation',
            method: 'save_html',
            args: [
                [translationId],
                $escapedElement.html() || $escapedElement.text() || '',
            ],
            context: this.options.recordInfo.context,
        });
    },
    /**
     * Save all "view" blocks.
     *
     * @private
     */
    _saveViewBlocks: async function () {
        const promises = [];
        const nodes = this.zoneMain.descendants(node => {
            return (
                node instanceof JWEditorLib.OdooStructureNode ||
                node instanceof JWEditorLib.OdooFieldNode
            );
        });
        for (const node of nodes) {
            const renderer = this.editor.plugins.get(JWEditorLib.Renderer);
            const renderedNode = (await renderer.render('dom/html', node))[0];
            $(renderedNode).find('.o_snippet_editor_updated').addBack().removeClass('o_snippet_editor_updated');
            let $saveNode = $(renderedNode).find('[data-oe-expression]');
            if ($saveNode.length === 0) {
                $saveNode = $(renderedNode)
            }
            const isStructureDirty = node instanceof JWEditorLib.OdooStructureNode && node.dirty;
            const isFieldDirty = node instanceof JWEditorLib.OdooFieldNode && node.fieldInfo.originalValue !== node.fieldInfo.value.get();
            if (isStructureDirty || isFieldDirty) {
                const promise = this._saveViewTo($saveNode, +$saveNode[0].dataset.oeId, node.xpath);
                promise.catch(() => { console.error('Fail to save:', $saveNode[0]); });
                promises.push(promise);
            }
        }
        return Promise.all(promises);
    },

    /**
     * Save all "cover properties" blocks.
     *
     * @private
     */
    _saveCoverPropertiesBlocks: async function (context) {
        let rpcResult;
        const wysiwygSaveCoverPropertiesBlocks = async () => {
            const covers = this.zoneMain.descendants(node => {
                const attributes = node.modifiers.find(JWEditorLib.Attributes);

                if (attributes && attributes.length && typeof attributes.get('class') === 'string') {
                    return attributes.classList.has('o_record_cover_container');
                }
            });
            const el = covers && covers[0] && this.editorHelpers.getDomNodes(covers[0])[0];
            if (!el) {
                console.warn('No cover found.');
                return;
            }

            var resModel = el.dataset.resModel;
            var resID = parseInt(el.dataset.resId);
            if (!resModel || !resID) {
                throw new Error('There should be a model and id associated to the cover.');
            }

            this.__savedCovers = this.__savedCovers || {};
            this.__savedCovers[resModel] = this.__savedCovers[resModel] || [];

            if (this.__savedCovers[resModel].includes(resID)) {
                return;
            }
            this.__savedCovers[resModel].push(resID);

            var cssBgImage = $(el.querySelector('.o_record_cover_image')).css('background-image');
            var coverProps = {
                'background-image': cssBgImage.replace(/"/g, '').replace(window.location.protocol + "//" + window.location.host, ''),
                'background_color_class': el.dataset.bgColorClass,
                'background_color_style': el.dataset.bgColorStyle,
                'opacity': el.dataset.filterValue,
                'resize_class': el.dataset.coverClass,
                'text_align_class': el.dataset.textAlignClass,
            };

            rpcResult = this._rpc({
                model: resModel,
                method: 'write',
                args: [
                    resID,
                    {'cover_properties': JSON.stringify(coverProps)}
                ],
            });
        };
        await context.execCommand(wysiwygSaveCoverPropertiesBlocks);
        return rpcResult;
    },
    /**
     * Save all "mega menu" classes.
     *
     * @private
     */
    _saveMegaMenuClasses: async function () {
        const structureNodes = this.zoneMain.descendants((node) => {
            return node.modifiers.get(JWEditorLib.Attributes).get('data-oe-field') === 'mega_menu_content';
        });
        const promises = [];
        for (const node of structureNodes) {
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            // FIXME: normally removing the 'show' class should not be necessary here
            // TODO: check that editor classes are removed here as well
            let promises = [];
            const items = node.modifiers.get(JWEditorLib.Attributes).classList.items();
            var classes = _.without(items, 'dropdown-menu', 'o_mega_menu', 'show');

            const itemId = node.modifiers.get(JWEditorLib.Attributes).get('data-oe-id');

            promises.push(this._rpc({
                model: 'website.menu',
                method: 'write',
                args: [
                    [parseInt(itemId)],
                    {
                        'mega_menu_classes': classes.join(' '),
                    },
                ],
            }));
        }

        await Promise.all(promises);
    },
    /**
     * Save all "newsletter" blocks.
     *
     * @private
     */
    _saveNewsletterBlocks: async function () {
        const defs = [];
        const wysiwygSaveNewsletterBlocks = async () => {
            defs.push(this._super.apply(this, arguments));
            const $popups = $(this.editorEditable).find('.o_newsletter_popup');
            for (const popup of $popups) {
                const $popup = $(popup);
                const content = $popup.data('content');
                if (content) {
                    defs.push(this._rpc({
                        route: '/website_mass_mailing/set_content',
                        params: {
                            'newsletter_id': parseInt($popup.attr('data-list-id')),
                            'content': content,
                        },
                    }));
                }
            }
        };
        await this.editor.execCommand(wysiwygSaveNewsletterBlocks);
        return Promise.all(defs);
    },
    /**
     * Save all modified images.
     *
     * @private
     */
    _saveModifiedImages: async function (context) {
        const wysiwygSaveModifiedImages = async (context) => {
            const defs = _.map(this._getEditable($('#wrapwrap')), async editableEl => {
                const {oeModel: resModel, oeId: resId} = editableEl.dataset;
                const proms = [...editableEl.querySelectorAll('.o_modified_image_to_save')].map(async el => {
                    const isBackground = !el.matches('img');
                    el.classList.remove('o_modified_image_to_save');

                    await this.editorHelpers.removeClass(context, el, 'o_modified_image_to_save');
                    // Modifying an image always creates a copy of the original, even if
                    // it was modified previously, as the other modified image may be used
                    // elsewhere if the snippet was duplicated or was saved as a custom one.
                    const newAttachmentSrc = await this._rpc({
                        route: `/web_editor/modify_image/${el.dataset.originalId}`,
                        params: {
                            res_model: resModel,
                            res_id: parseInt(resId),
                            data: (isBackground ? el.dataset.bgSrc : el.getAttribute('src')).split(',')[1],
                        },
                    });
                    if (isBackground) {
                        await this.editorHelpers.setStyle(context, el, 'background-image', `url('${newAttachmentSrc}')`);
                        await this.editorHelpers.setAttribute(context, el, 'data-bgSrc', '');
                    } else {
                        await this.editorHelpers.setAttribute(context, el, 'src', newAttachmentSrc);
                    }
                });
                return Promise.all(proms);
            });
            await Promise.all(defs);
        };
        return context.execCommand(wysiwygSaveModifiedImages);
    },
    /**
     * Initialize the editor for a translation.
     *
     * @private
     */
    _setupTranslation: function () {
        const attrs = ['placeholder', 'title', 'alt'];
        const nodesToTranslateAttributes = this.zoneMain.descendants(node => {
            const attributes = node.modifiers.find(JWEditorLib.Attributes);
            return attributes && attributes.keys().some(key => attrs.includes(key));
        });
        const domNodesToTranslateAttributes = nodesToTranslateAttributes.flatMap(nodeToTranslateAttributes => {
            return this.editorHelpers.getDomNodes(nodeToTranslateAttributes)[0];
        });
        this.$nodesToTranslateAttributes = $(domNodesToTranslateAttributes);
        for (const attr of attrs) {
            this.$nodesToTranslateAttributes.each(function () {
                var $node = $(this);
                var translation = $node.data('translation') || {};
                var attributeTranslation = $node.attr(attr);
                if (attributeTranslation) {
                    var match = attributeTranslation.match(/<span [^>]*data-oe-translation-id="([0-9]+)"[^>]*>(.*)<\/span>/);
                    var $translatedAttributeNode = $(attributeTranslation).addClass('d-none o_editable o_editable_translatable_attribute').appendTo('body');
                    $translatedAttributeNode.data('$node', $node).data('attribute', attr);

                    translation[attr] = $translatedAttributeNode[0];
                    if (match) {
                        $node.attr(attr, match[2]);
                    }
                }
                var select2 = $node.data('select2');
                if (select2) {
                    select2.blur();
                    $node.on('translate', function () {
                        select2.blur();
                    });
                    $node = select2.container.find('input');
                }
                $node.addClass('o_translatable_attribute').data('translation', translation);
            });
        }
        this.$attribute_translations = $('.o_editable_translatable_attribute');
        this.translations = [];
        this._markTranslatableNodes();

        // We don't want the BS dropdown to close
        // when clicking in a element to translate
        $('.dropdown-menu').on('click', '.o_editable', function (ev) {
            ev.stopPropagation();
        });
    },
    /**
     * Save all translation blocks.
     *
     * @private
     */
    _onSaveTranslation: async function (context) {
        const defs = [];
        this.trigger_up('edition_will_stopped');
        this.trigger_up('ready_to_save', {defs: defs});
        await Promise.all(defs);

        const promises = [];
        const translationContainers = {};
        const getTranslationNodes = () => {
            let previousTranslationId;
            this.zoneMain.descendants(descendant => {
                const format = descendant.modifiers.find(JWEditorLib.OdooTranslationFormat);
                const translationId = format && format.translationId;
                if (translationId && this.editor.mode.is(descendant, 'editable')) {
                    translationContainers[translationId] = translationContainers[translationId] || [];
                    const containers = translationContainers[translationId];
                    if (previousTranslationId !== translationId) {
                        containers.push(new JWEditorLib.ContainerNode());
                    }
                    const lastContainer = containers[containers.length-1];
                    lastContainer.append(descendant.clone());
                }
                previousTranslationId = translationId;
            });
        }
        await context.execCommand(getTranslationNodes);

        // Save the odoo translation formats.
        for (const id of Object.keys(translationContainers)) {
            const containers = translationContainers[id];
            // todo: check that all container render the same way otherwise
            // inform the user that there is conflict between the same
            // traduction.
            const lastContainer = containers[containers.length-1];
            const translationNode = lastContainer.children()[0];
            const renderer = this.editor.plugins.get(JWEditorLib.Renderer);

            const renderedNode = (await renderer.render('dom/html', lastContainer))[0].firstChild;
            const translationFormat = translationNode.modifiers.find(JWEditorLib.OdooTranslationFormat);

            let $renderedTranslation = $(renderedNode);
            if (!$renderedTranslation.data('oe-translation-state')) {
                $renderedTranslation = $renderedTranslation.find('[data-oe-translation-state]');
            }

            if (translationFormat.translationId) {
                promises.push(this._saveTranslationTo($renderedTranslation, +translationFormat.translationId));
            } else {
                const attributes = translationFormat.modifiers.find(JWEditorLib.Attributes);
                promises.push(this._saveViewTo(
                    $renderedTranslation,
                    attributes.get('data-oe-id'),
                    attributes.get('data-oe-xpath')
                ));
            }
        }

        // Save attributes
        for (const attribute_translation of this.$attribute_translations) {
            const $attribute_translations = $(attribute_translation);
            promises.push(this._saveTranslationTo(
                $attribute_translations,
                +$attribute_translations.data('oe-translation-id')
            ));
        }

        await Promise.all(promises);
        this.trigger_up('edition_was_stopped');
        window.location.reload();
    },
    /**
     * Returns the editable areas on the page.
     *
     * @param {JQuery} $element
     * @returns {JQuery}
     */
    _getEditable($element) {
        return $element.find('[data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                var $parent = $(this).closest('.o_editable, .o_not_editable');
                return !$parent.length || $parent.hasClass('o_editable');
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .not('hr, br, input, textarea')
            .add('.o_editable');
    },
    /**
     * Additional binding after start.
     *
     * Meant to be overridden
     */
    _bindAfterStart() {},
});

//--------------------------------------------------------------------------
// Public helper
//--------------------------------------------------------------------------
/**
 * @param {Node} node (editable or node inside)
 * @returns {Object}
 * @returns {Node} sc - start container
 * @returns {Number} so - start offset
 * @returns {Node} ec - end container
 * @returns {Number} eo - end offset
 */
Wysiwyg.getRange = function (node) {
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    var result = range && {
        sc: range.startContainer,
        so: range.startOffset,
        ec: range.endContainer,
        eo: range.endOffset,
    };
    return result;
};
/**
 * @param {Node} startNode
 * @param {Number} startOffset
 * @param {Node} endNode
 * @param {Number} endOffset
 */
Wysiwyg.setRange = async function (wysiwyg, startNode, startOffset, endNode, endOffset) {
    endNode = endNode || startNode;
    endOffset = endOffset || startOffset-1;
    const wysiwygSetRange = async () => {
        const startVNode = wysiwyg.editorHelpers.getNodes(startNode);
        const endVNode = wysiwyg.editorHelpers.getNodes(endNode);
        wysiwyg.editor.selection.select(startVNode[startOffset], endVNode[endOffset]);
    };
    await wysiwyg.editor.execCommand(wysiwygSetRange);
};

return Wysiwyg;
});
