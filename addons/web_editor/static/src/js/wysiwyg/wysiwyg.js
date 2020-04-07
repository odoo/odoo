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
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js
     * @options {Object} options.attachments
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
                            return attributes &&
                                (
                                    attributes.classList.has('o_not_editable') ||
                                    attributes.has('data-oe-readonly')
                                );
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

                    // o_header_standard and its descendants.
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

                    // blockquote and alert snippets and their descendants:
                    {
                        selector: [node => {
                            const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                            return attributes && (
                                attributes.classList.has('s_blockquote') ||
                                attributes.classList.has('s_alert')
                            );
                        }],
                        properties: {
                            editable: {
                                value: false,
                                cascading: true,
                            },
                        },
                    },
                    {
                        selector: [node => {
                            // Blockquote and alert snippets's children are not
                            // editable...
                            const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                            return attributes && (
                                attributes.classList.has('s_blockquote') ||
                                attributes.classList.has('s_alert')
                            );
                        }, node => {
                            // ...except for their _content child and its
                            // descendants.
                            const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                            return attributes && (
                                attributes.classList.has('s_blockquote_content') ||
                                attributes.classList.has('s_alert_content')
                            );
                        }],
                        properties: {
                            editable: {
                                value: true,
                                cascading: true,
                            },
                        },
                    },

                    // s_process_step
                    {
                        selector: [node => {
                            const attributes = node.modifiers.find(this.JWEditorLib.Attributes);
                            return attributes && attributes.classList.has('s_process_step_icon');
                        }],
                        properties: {
                            editable: {
                                value: false,
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
            openTextColorPicker: { handler: this.toggleTextColorPicker.bind(this) },
            openBackgroundColorPicker: { handler: this.toggleBackgroundColorPicker.bind(this) },
            discardOdoo: { handler: this.discardEditions.bind(this) },
            saveOdoo: { handler: this.saveContent.bind(this) },
        };
        if (!this.options.enableTranslation) {
            Object.assign(customCommands, {
                openMedia: { handler: this.openMediaDialog.bind(this) },
                openLinkDialog: { handler: this.openLinkDialog.bind(this) },
                cropImage: { handler: this.cropImage.bind(this) },
                transformImage: { handler: this.transformImage.bind(this) },
                describeImage: { handler: this.describeImage.bind(this) },
            });
        }
        const plugins = []
        if (this.options.enableWebsite && !this.options.enableTranslation) {
            plugins.push([JWEditorLib.OdooField]);
        }
        if (this.options.enableResizer) {
            plugins.push([JWEditorLib.Resizer]);
        }
        this.editor = new JWEditorLib.OdooWebsiteEditor(Object.assign({}, this.options, {
            snippetMenuElement: $mainSidebar[0],
            snippetManipulators: $snippetManipulators[0],
            customCommands: Object.assign(customCommands, this.options.customCommands),
            plugins: plugins,
            source: this.value,
            location: this.options.location || [this.el, 'replace'],
            mode: this._modeConfig,
        }));

        if (typeof odoo.debug === 'string' && config.isDebug('assets') && JWEditorLib.DevTools) {
            this.editor.load(JWEditorLib.DevTools);
        }
        await this.editor.start();
        this._bindAfterStart();


        this.editorHelpers = this.editor.plugins.get(JWEditorLib.DomHelpers);
        const domLayout = this.editor.plugins.get(JWEditorLib.Layout).engines.dom;
        this.zoneMain = domLayout.root.firstDescendant(node => node.managedZones && node.managedZones.includes('main'));
        const rootElement = this.editorHelpers.getDomNodes(domLayout.root.firstDescendant(JWEditorLib.ContainerNode))[0];
        this.editorEditable = this.editorHelpers.getDomNodes(this.zoneMain)[0] || this.editorHelpers.getDomNodes(this.zoneMain.parent)[0];

        this.$toolbar = $(rootElement).find('jw-toolbar').detach();

        if (this.options.enableWebsite) {
            const $wrapwrap = $('#wrapwrap');
            $wrapwrap.removeClass('o_editable'); // clean the dom before edition
            this._getEditable($wrapwrap).addClass('o_editable o_editable_no_shadow');
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

        // Make sure to warn the user if they're about to leave the page and
        // they have changes that would be lost if they did.
        let flag = false;
        window.onbeforeunload = () => {
            if (!flag) {
                flag = true;
                _.defer(() => (flag = false));
                return _t('This document is not saved!');
            }
        };

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

            // Place the history buttons in their right location.
            const $undoButton = $('<button name="undo" class="btn btn-secondary fa fa-undo"></button>');
            const $redoButton = $('<button name="redo" class="btn btn-secondary fa fa-repeat"></button>');
            $undoButton.on('click', () => this.editor.execCommand('undo'));
            $redoButton.on('click', () => this.editor.execCommand('redo'));
            const reactiveEditorInfo = this.editor.plugins.get(JWEditorLib.ReactiveEditorInfo);
            const updateButtons = () => {
                const state = reactiveEditorInfo.editorInfo.get();
                state.canUndo ? $undoButton.removeAttr('disabled') : $undoButton.attr('disabled', true);
                state.canRedo ? $redoButton.removeAttr('disabled') : $redoButton.attr('disabled', true);
            };
            reactiveEditorInfo.editorInfo.on('set', updateButtons);
            updateButtons();

            $('.o_we_website_top_actions .o_we_external_history_buttons').append($undoButton, $redoButton);

            this.$el.on('content_changed', function (e) {
                self.trigger_up('wysiwyg_change');
            });

            const onCommitCheckSnippets = (params) => {
                const range = this.editor.selection.range;
                let currentSelectionType = "text";
                if(!range.isCollapsed()) {
                    const nextStartSibling = range.start.nextSibling();
                    const prevEndSibling = range.end.previousSibling();
                    if (nextStartSibling && prevEndSibling && nextStartSibling.id === prevEndSibling.id) {
                        switch (nextStartSibling.name) {
                            case "ImageNode":
                                currentSelectionType = "image";
                                break;
                            case "OdooVideoNode":
                                currentSelectionType = "video";
                                break;
                            case "FontAwesomeNode":
                                currentSelectionType = "picto";
                                break;
                            default:
                                currentSelectionType = "text";
                                break;
                        }

                    }
                }
                this.snippetsMenu.updateJabberwockToolbarContainer(currentSelectionType);//.bind(this.snippetsMenu);
                this.snippetsMenu.updateCurrentSnippetEditorOverlay();

                if (params.commandNames.includes('undo') || params.commandNames.includes('redo')) {
                    setTimeout(() => {
                        // use setTimeout to reload snippets after the redraw
                        this.snippetsMenu.trigger('reload_snippet_dropzones');
                    });
                }
            };
            const onSelectionUpdateColorPreview = (param) => {
                let color, bgColor = undefined;

                const findColorsIn = (object) => {
                    const attributes = object.modifiers.find(JWEditorLib.Attributes);
                    const curentTextStyle = attributes ? attributes.style : false;
                    if (curentTextStyle && !color) {
                        color = curentTextStyle.get('color') ;
                    }
                    if (curentTextStyle && !bgColor) {
                        bgColor = curentTextStyle.get('background-color');
                    }
                }

                const rangeStart = param.context.range.start
                const node = rangeStart.nextSibling(node => !(node instanceof JWEditorLib.SeparatorNode) || rangeStart.nextSibling())
                if(node) {
                    findColorsIn(node);
                    if (!color || !bgColor) {
                        const formats = node.modifiers.filter(JWEditorLib.Format);
                        for (const format of formats) {
                            findColorsIn(format)
                        }
                    }
                }

                if(!color) color = "#000";
                if(!bgColor) bgColor = "rgba(255,255,255,0)";

                this.$toolbar.find(".jw-dropdown-textcolor>jw-button").css("background-color", color);
                this.$toolbar.find(".jw-dropdown-backgroundcolor>jw-button").css("background-color", bgColor);
            }
            this.editor.dispatcher.registerCommandHook('setSelection', onSelectionUpdateColorPreview);
            this.editor.dispatcher.registerCommandHook('@commit', onCommitCheckSnippets);

        } else {
            return _super.apply(this, arguments);
        }
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
    discardEditions: async function () {
        let self = this;
        return new Promise(function (resolve, reject) {
            // Only show an alert if there is a risk that changes would be lost.
            if (self.isDirty()) {
                const confirmMessage = `If you discard the current edits, all
                    unsaved changes will be lost. You can cancel to return to
                    edit mode.`.replace(/[\n\s]+/g, ' ');
                const confirm = Dialog.confirm(this, _t(confirmMessage), {
                    confirm_callback: resolve,
                });
                confirm.on('closed', self, reject);
            } else {
                resolve();
            }
        }).then(function () {
            window.onbeforeunload = null;
            window.location.reload();
        });
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
     * Return dirty Odoo structure nodes and Odoo field nodes.
     *
     * @returns {Array<OdooStructureNode | OdooFieldNode>}
     */
    getDirtyNodes: function () {
        return this.zoneMain.descendants(node => {
            if (node instanceof JWEditorLib.OdooStructureNode) {
                return node.dirty;
            } else if (node instanceof JWEditorLib.OdooFieldNode) {
                return node.fieldInfo.originalValue !== node.fieldInfo.value.get();
            }
        });
    },
    /**
     * Return the editable area.
     *
     * @returns {jQuery}
     */
    getEditable: function () {
        return this.$editor;
    },
    getFormatInfo: function() {
        return this.editor.plugins.get(JWEditorLib.Odoo).formatInfo;
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
                this._setColor(colorpicker, setCommandId, unsetCommandId, e.data.color, $dropdownNode);
            });
            colorpicker.on('color_picked', this, (e) => {
                this._setColor(colorpicker, setCommandId, unsetCommandId, e.data.color, $dropdownNode, true);
            });
            colorpicker.on('color_hover', this, (e) => {
                this._setColor(colorpicker, setCommandId, unsetCommandId, e.data.color, $dropdownNode, false);
            });
            colorpicker.on('color_leave', this, (e) => {
                this._setColor(colorpicker, 'undo', 'undo', undefined, $dropdownNode, false);
            });
        }
    },
    /**
     * Return true if the content has changed.
     *
     * @returns {boolean}
     */
    isDirty: function () {
        return !!this.getDirtyNodes().length;
    },
    async openLinkDialog(params) {
        const range = this.editor.selection.range;
        const Link = JWEditorLib.Link;

        const previousNode = range.start.previousSibling();
        const nextNode = range.start.nextSibling();
        const node = previousNode && (Link.isLink(previousNode) || !nextNode) ? previousNode : nextNode;
        const currentLink = node && Link.isLink(node) && node.modifiers.find(JWEditorLib.LinkFormat);

        let text = '';
        const images = [];
        const domSelection = this.editorEditable.ownerDocument.getSelection();
        if (domSelection.rangeCount) {
            let domRange = domSelection.getRangeAt(0);
            const ancestor = domRange.commonAncestorContainer.nodeType === Node.ELEMENT_NODE ?
                domRange.commonAncestorContainer : domRange.commonAncestorContainer.parentNode;

            let container;
            if (domSelection.isCollapsed && currentLink) {
                // If colapse in a link, select all the link.
                container = ancestor.closest('a');
                const nodes = this.editorHelpers.getNodes(container);
                await params.context.execCommand('setSelection', {
                    vSelection: {
                        anchorNode: nodes[0],
                        anchorPosition: 'BEFORE',
                        focusNode: nodes[nodes.length - 1],
                        focusPosition: 'AFTER',
                        direction: 'FORWARD',
                    },
                });
            } else {
                // If a selection exists, create a text value with \n to split each block (for the preview)
                domRange = domSelection.getRangeAt(0);
                container = document.createElement('w-clone');
                container.appendChild(domRange.cloneContents());
                ancestor.appendChild(container);
            }

            const blocks = [''];
            let domNode = container && container.firstChild;
            if (domNode) {
                while (domNode.childNodes && domNode.childNodes.length) {
                    domNode = domNode.childNodes[0];
                }
                while (domNode && domNode !== container) {
                    if (domNode.nodeName === 'IMG' || domNode.classList && domNode.classList.contains('fa')) {
                        images.push(domNode.outerHTML);
                        blocks[blocks.length - 1] += '[IMG]';
                    } else if (domNode.classList && domNode.classList.contains('media_iframe_video')) {
                        blocks.push('');
                    } else if (domNode.nodeType === Node.ELEMENT_NODE && window.getComputedStyle(domNode).display === 'block') {
                        blocks.push('');
                    } else if (domNode.nodeType === Node.TEXT_NODE) {
                        blocks[blocks.length - 1] += domNode.textContent;
                    }

                    if (domNode.childNodes && domNode.childNodes.length) {
                        domNode = domNode.childNodes[0];
                    } else if (domNode.nextSibling) {
                        domNode = domNode.nextSibling;
                    } else {
                        while (domNode && !domNode.nextSibling && domNode !== container) {
                            domNode = domNode.parentNode;
                        }
                        domNode = domNode && domNode !== container && domNode.nextSibling;
                    }
                }
                text = blocks.filter(str => str.length).join('\n');
            }

            if (!domSelection.isCollapsed || !currentLink) {
                container.remove();
            }
        }

        const modifiers = range.modifiers;
        const linkFormat = modifiers && modifiers.find(JWEditorLib.LinkFormat);
        let classes = '';
        let target;
        if (currentLink) {
            const linkAttributes = currentLink.modifiers.find(JWEditorLib.Attributes);
            classes = (linkAttributes && linkAttributes.get('class')) || '';
            target = linkAttributes && linkAttributes.get('target');
        }

        const coloredLevelParent = node ? node.ancestor(cNode => {
            const attributes = cNode.modifiers.find(JWEditorLib.Attributes);
            return attributes && attributes.get('class') && attributes.get('class').includes('o_cc')
        }) : false;

        let colorCombinationClass = "";
        if (coloredLevelParent) {
            let allClasses = coloredLevelParent.modifiers.find(JWEditorLib.Attributes).get('class').split(" ");
            colorCombinationClass = allClasses.find(classStr => classStr.match(/o_cc[0-9]+/));
        }

        const linkDialog = new weWidgets.LinkDialog(this,
            {
                props: {
                    text: text,
                    images: images,
                    url: linkFormat && linkFormat.url || '',
                    initialClassNames: classes,
                    colorCombinationClass: colorCombinationClass,
                    target: target,

                    __editorEditable: this.editorEditable,
                },
            },
        );
        linkDialog.open();
        linkDialog.on('save', this, async (params)=> {
            const onSaveLinkDialog = async (context) => {
                const linkParams = {
                    url: params.url,
                    label: range.isCollapsed() && params.text,
                    target: params.isNewWindow ? '_blank' : '',
                };
                const nodes = range.targetedNodes(JWEditorLib.InlineNode);
                await context.execCommand('link', linkParams);
                const links = nodes.map(node => node.modifiers.find(JWEditorLib.LinkFormat)).filter(f => f);
                for (const link of links) {
                    link.modifiers.get(JWEditorLib.Attributes).set('class', params.classes);
                }
            };
            await this.editor.execCommand(onSaveLinkDialog);
        });
    },
    openMediaDialog(params) {
        const nodes = params.media ? [params.media] : params.context.range.selectedNodes();
        const node = nodes[0];
        let $baseNode;

        if (nodes.length === 1) {
            if (node instanceof JWEditorLib.FontAwesomeNode || node instanceof JWEditorLib.OdooVideoNode) {
                const originalDomNode = this.editorHelpers.getDomNodes(node).filter(dom => dom.nodeType === Node.ELEMENT_NODE);
                $baseNode = $(originalDomNode).clone();
            } else if (node instanceof JWEditorLib.ImageNode) {
                $baseNode = $(this.editorHelpers.getDomNodes(node).filter(dom => dom.nodeType === Node.ELEMENT_NODE));
            }
            if (node instanceof JWEditorLib.FontAwesomeNode) {
                params.htmlClass = [...$baseNode[0].classList].filter((className) => {
                    return !className.startsWith('fa') || faZoomClassRegex.test(className);
                }).join(' ');
            }
        }

        // avoid circular reference
        delete params.context;

        let mediaDialog = new weWidgets.MediaDialog(this, params, $baseNode);
        mediaDialog.open();
        mediaDialog.on('save', this, async (element) => {
            // If we're not _replacing_ a media (done by media dialog), insert it.
            if (!$baseNode || $baseNode.length !== 1 || !$(element).is($baseNode[0].nodeName)) {
                if (params.htmlClass) {
                    element.className += " " + params.htmlClass;
                }
                await this.editor.execCommand('insertMedia', { element: element });
            }
        });
    },
    async saveContent(context = this.editor) {
        if (this.options.enableTranslation) {
            await this._onSaveTranslation(context);
        } else {
            await this.saveToServer(context);
        }
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
                window.onbeforeunload = null;
                if (reload) {
                    window.location.reload();
                }
            }).catch(error => {
                console.error('Impossible to save.', error);
            });
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
    transformImage: async function (params) {
        const imageNodes = params.context.range.targetedNodes(JWEditorLib.ImageNode);
        const imageNode = imageNodes.length === 1 && imageNodes[0];
        if (imageNode) {
            const domEngine = this.editor.plugins.get(JWEditorLib.Layout).engines.dom;
            const $node = $(domEngine.getDomNodes(imageNode)[0]);
            this._transform($node);
        }
    },
    async updateChanges($target, context = this.editor) {
        const updateChanges = async (context) => {
            const html = $target.html();
            $target.html('');
            const attributes = [...$target[0].attributes].reduce( (acc, attribute) => {
                acc[attribute.name] = attribute.value;
                return acc
            }, {});
            await this.editorHelpers.updateAttributes(context, $target[0], attributes);
            await this.editorHelpers.empty(context, $target[0]);
            await this.editorHelpers.insertHtml(context, html, $target[0], 'INSIDE');
        };
        await context.execCommand(updateChanges);
    },
    withDomMutationsObserver ($target, callback) {
        callback();
        this.updateChanges($target);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Additional binding after start.
     *
     * Meant to be overridden
     */
    _bindAfterStart() {},
    /**
     * Returns the editable areas on the page.
     *
     * @param {JQuery} $element
     * @returns {JQuery}
     */
    _getEditable($element) {
        const $editable = $element.find('[data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                var $parent = $(this).closest('.o_editable, .o_not_editable');
                return !$parent.length || $parent.hasClass('o_editable');
            })
            .not('link, script')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .not('hr, br, input, textarea')
            .add('.o_editable');
        if (this.options.enableTranslation) {
            const selector = '[data-oe-translation-id], '+
                '[data-oe-model][data-oe-id][data-oe-field], ' +
                '[placeholder*="data-oe-translation-id="], ' +
                '[title*="data-oe-translation-id="], ' +
                '[alt*="data-oe-translation-id="]';
            $editable.filter(':has(' + selector + ')').attr('data-oe-readonly', true);
        }
        return $editable.not('[data-oe-readonly]')
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
                const formatAttributes = format && format.modifiers.find(JWEditorLib.Attributes);
                const translationId = format && (format.translationId || +formatAttributes.get('data-oe-id'));
                if (this.editor.mode.is(descendant, 'editable')) {
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
            let $saveNode = $(renderedNode).find('[data-oe-expression][data-oe-id]');
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
    _setColor(colorpicker, setCommandId, unsetCommandId, color, $dropDownToToggle, closeColorPicker = false) {
        if(color === "") {
            this.editor.execCommand(unsetCommandId);
        } else {
            if (colorpicker.colorNames.indexOf(color) !== -1) {
                // todo : find a better way to detect and send css variable
                color = "var(--" + color + ")";
            }
            this.editor.execCommand(setCommandId, {color: color});
        }
        const $jwButton = $dropDownToToggle.find(".dropdown-toggle")
        // Only adapt the color preview in the toolbar for the web_editor.
        if(this.options.snippets) $jwButton.css("background-color", color);
        if(closeColorPicker) {
            $jwButton.dropdown("toggle");
            colorpicker.selectedColor = '';
        }
    },
    /**
     * Initialize the editor for a translation.
     *
     * @private
     */
    _setupTranslation: function () {
        const attributeNames = ['placeholder', 'title', 'alt'];
        const nodesToTranslateAttributes = this.zoneMain.descendants(node => {
            const attributes = node.modifiers.find(JWEditorLib.Attributes);
            return attributes && attributes.keys().some(key => {
                if (attributeNames.includes(key)) {
                    const div = document.createElement('div');
                    div.innerHTML = attributes.get(key);
                    // The attribute is translatable if its value is the HTML
                    // of a node with attributes that include
                    // data-oe-translation-state.
                    return div.querySelector('[data-oe-translation-state]');
                }
            });
        });
        const domNodesToTranslateAttributes = nodesToTranslateAttributes.flatMap(nodeToTranslateAttributes => {
            return this.editorHelpers.getDomNodes(nodeToTranslateAttributes)[0];
        });
        this.$nodesToTranslateAttributes = $(domNodesToTranslateAttributes);
        for (const attr of attributeNames) {
            this.$nodesToTranslateAttributes.each(function () {
                var $node = $(this);
                var translation = $node.data('translation') || {};
                var attributeTranslation = $node.attr(attr);
                if (attributeTranslation) {
                    var match = attributeTranslation.match(/<span [^>]*data-oe-translation-id="([0-9]+)"[^>]*>(.*)<\/span>/);
                    if (match) {
                        var $translatedAttributeNode = $(attributeTranslation).addClass('d-none o_editable o_editable_translatable_attribute').appendTo('body');
                        $translatedAttributeNode.data('$node', $node).data('attribute', attr);
                        translation[attr] = $translatedAttributeNode[0];
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

        // Add a tooltip for not-editable areas
        $(document.body)
            .tooltip({
                selector: '[data-oe-readonly], .o_not_editable',
                container: 'body',
                trigger: 'hover',
                delay: { 'show': 1000, 'hide': 100 },
                placement: 'bottom',
                title: _t("Readonly field")
            })
            .on('click', function () {
                $(this).tooltip('hide');
            });
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
    _updateAttributes(node) {
        const attributes = {}
        for (const attr of node.attributes){
            attributes[attr.name] = attr.value;
        }
        this.editorHelpers.updateAttributes(this.editor, node, attributes);
    },
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
