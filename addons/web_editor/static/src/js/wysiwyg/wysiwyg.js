odoo.define('web_editor.wysiwyg', function (require) {
'use strict';

var Widget = require('web.Widget');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var modulesRegistry = require('web_editor.wysiwyg.plugin.registry');
var wysiwygOptions = require('web_editor.wysiwyg.options');

var _t = core._t;

var Wysiwyg = Widget.extend({
    xmlDependencies: [
        '/web_editor/static/src/xml/wysiwyg.xml',
    ],
    custom_events: {
        getRecordInfo: '_onGetRecordInfo',
        wysiwyg_blur: '_onWysiwygBlur',
    },
    defaultOptions: {
        codeview: config.debug,
        recordInfo: {
            context: {},
        },
    },

    /**
     * @params {Object} params
     * @params {Object} params.recordInfo
     * @params {Object} params.recordInfo.context
     * @params {String} [params.recordInfo.context]
     * @params {integer} [params.recordInfo.res_id]
     * @params {String} [params.recordInfo.data_res_model]
     * @params {integer} [params.recordInfo.data_res_id]
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js
     * @params {Object} params.attachments
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js (for attachmentIDs)
     * @params {function} params.generateOptions
     *   called with the summernote configuration object used before sending to summernote
     *   @see _editorOptions
     **/
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.options = _.extend({}, this.defaultOptions, params);
        this.attachments = this.options.attachments || [];
        this.hints = [];
        this.$el = null;
        this._dirty = false;
        this.id = _.uniqueId('wysiwyg_');
    },
    /**
     * Load assets and color picker template then call summernote API
     * and replace $el by the summernote editable node.
     *
     * @override
     **/
    willStart: function () {
        var self = this;
        this.$target = this.$el;
        this.$el = null; // temporary null to avoid hidden error, setElement when start
        return this._super()
            .then(function () {
                return modulesRegistry.start(self).then(function () {
                    return self._loadInstance();
                });
            });
    },
    /**
     *
     * @override
     */
    start: function () {
        var value = this._summernote.code();
        this._value = value;
        if (this._summernote.invoke('HelperPlugin.hasJinja', value)) {
            this._summernote.invoke('codeview.forceActivate');
        }
        return Promise.resolve();
    },
    /**
     * @override
     */
    destroy: function () {
        if (this._summernote) {
            // prevents the replacement of the target by the content of summernote
            // (in order to be able to cancel)
            var removeLayout = $.summernote.ui.removeLayout;
            $.summernote.ui.removeLayout = function ($note, layoutInfo) {
                layoutInfo.editor.remove();
                $note.show();
            };
            this._summernote.destroy();
            $.summernote.ui.removeLayout = removeLayout;
        }
        this.$target.removeAttr('data-wysiwyg-id');
        this.$target.removeData('wysiwyg');
        $(document).off('.' + this.id);
        this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a step (undo) in editor.
     */
    addHistoryStep: function () {
        var editor = this._summernote.modules.editor;
        editor.createRange();
        editor.history.recordUndo();
    },
    /**
     * Return the editable area.
     *
     * @returns {jQuery}
     */
    getEditable: function () {
        if (this._summernote.invoke('HelperPlugin.hasJinja', this._summernote.code())) {
            return this._summernote.layoutInfo.codable;
        } else if (this._summernote.invoke('codeview.isActivated')) {
            this._summernote.invoke('codeview.deactivate');
        }
        return this._summernote.layoutInfo.editable;
    },
    /**
     * Perform undo or redo in the editor.
     *
     * @param {integer} step
     */
    history: function (step) {
        if (step < 0) {
            while (step) {
                this._summernote.modules.editor.history.rewind();
                step++;
            }
        } else if (step > 0) {
            while (step) {
                this._summernote.modules.editor.history.redo();
                step--;
            }
        }
    },
    /**
     * Return true if the content has changed.
     *
     * @returns {Boolean}
     */
    isDirty: function () {
        if (!this._dirty && this._value !== this._summernote.code()) {
            console.warn("not dirty flag ? Please fix it.");
        }
        return this._value !== this._summernote.code();
    },
    /**
     * Return true if the current node is unbreakable.
     * An unbreakable node can be removed or added but can't by split into
     * different nodes (for keypress and selection).
     * An unbreakable node can contain nodes that can be edited.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isUnbreakableNode: function (node) {
        return ["TD", "TR", "TBODY", "TFOOT", "THEAD", "TABLE"].indexOf(node.tagName) !== -1 || $(node).is(this.getEditable()) ||
            !this.isEditableNode(node.parentNode) || !this.isEditableNode(node) || $.summernote.dom.isMedia(node);
    },
    /**
     * Return true if the current node is editable (for keypress and selection).
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isEditableNode: function (node) {
        return $(node).is(':o_editable') && !$(node).is('table, thead, tbody, tfoot, tr');
    },
    /**
     * Set the focus on the element.
     */
    focus: function () {
        this.$el.mousedown();
    },
    /**
     * Get the value of the editable element.
     *
     * @param {object} [options]
     * @param {Boolean} [options.keepPopover]
     * @returns {String}
     */
    getValue: function (options) {
        if (!options || !options.keepPopover) {
            this._summernote.invoke('editor.hidePopover');
        }
        var $editable = this.getEditable().clone();
        $editable.find('.o_wysiwyg_to_remove').remove();
        $editable.find('[contenteditable]').removeAttr('contenteditable');
        $editable.find('.o_fake_not_editable').removeClass('o_fake_not_editable');
        $editable.find('.o_fake_editable').removeClass('o_fake_editable');
        $editable.find('[class=""]').removeAttr('class');
        $editable.find('[style=""]').removeAttr('style');
        $editable.find('[title=""]').removeAttr('title');
        $editable.find('[alt=""]').removeAttr('alt');
        $editable.find('[data-original-title=""]').removeAttr('data-original-title');
        $editable.find('a.o_image, span.fa, i.fa').html('');
        $editable.find('[aria-describedby]').removeAttr('aria-describedby').removeAttr('data-original-title');

        return $editable.html() || $editable.val();
    },
    /**
     * Save the content in the target
     *      - in init option beforeSave
     *      - receive editable jQuery DOM as attribute
     *      - called after deactivate codeview if needed
     * @returns {Promise}
     *      - resolve with true if the content was dirty
     */
    save: function () {
        var isDirty = this.isDirty();
        var html = this.getValue();
        if (this.$target.is('textarea')) {
            this.$target.val(html);
        } else {
            this.$target.html(html);
        }
        return Promise.resolve({isDirty:isDirty, html:html});
    },
    /**
     * @param {String} value
     * @param {Object} options
     * @param {Boolean} [options.notifyChange]
     * @returns {String}
     */
    setValue: function (value, options) {
        if (this._summernote.invoke('HelperPlugin.hasJinja', value)) {
            this._summernote.invoke('codeview.forceActivate');
        }
        this._dirty = true;
        this._summernote.invoke('HistoryPlugin.clear');
        this._summernote.invoke('editor.hidePopover');
        this._summernote.invoke('editor.clearTarget');
        var $editable = this.getEditable().html(value + '');
        this._summernote.invoke('UnbreakablePlugin.secureArea');
        if (!options || options.notifyChange !== false) {
            $editable.change();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Object} the summernote configuration
     */
    _editorOptions: function () {
        var self = this;
        var allowAttachment = !this.options.noAttachment;

        var options = JSON.parse(JSON.stringify(wysiwygOptions));

        options.parent = this;
        options.lang = "odoo";

        options.focus = false;
        options.disableDragAndDrop = !allowAttachment;
        options.styleTags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre'];
        options.fontSizes = [_t('Default'), '8', '9', '10', '11', '12', '13', '14', '18', '24', '36', '48', '62'];
        options.minHeight = 180;

        options.keyMap.pc['CTRL+K'] = 'LinkPlugin.show';
        options.keyMap.mac['CMD+K'] = 'LinkPlugin.show';
        delete options.keyMap.pc['CTRL+LEFTBRACKET'];
        delete options.keyMap.mac['CMD+LEFTBRACKET'];
        delete options.keyMap.pc['CTRL+RIGHTBRACKET'];
        delete options.keyMap.mac['CMD+RIGHTBRACKET'];

        options.toolbar = [
            ['style', ['style']],
            ['font', ['bold', 'italic', 'underline', 'clear']],
            ['fontsize', ['fontsize']],
            ['color', ['colorpicker']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['table', ['table']],
            ['insert', allowAttachment ? ['linkPlugin', 'mediaPlugin'] : ['linkPlugin']],
            ['history', ['undo', 'redo']],
            ['view', this.options.codeview ? ['fullscreen', 'codeview', 'help'] : ['fullscreen', 'help']]
        ];
        options.popover = {
            image: [
                ['padding'],
                ['imagesize', ['imageSizeAuto', 'imageSize100', 'imageSize50', 'imageSize25']],
                ['float', ['alignLeft', 'alignCenter', 'alignRight', 'alignNone']],
                ['imageShape'],
                ['cropImage'],
                ['media', ['mediaPlugin', 'removePluginMedia']],
                ['alt']
            ],
            video: [
                ['padding'],
                ['imagesize', ['imageSize100', 'imageSize50', 'imageSize25']],
                ['float', ['alignLeft', 'alignCenter', 'alignRight', 'alignNone']],
                ['media', ['mediaPlugin', 'removePluginMedia']]
            ],
            icon: [
                ['padding'],
                ['faSize'],
                ['float', ['alignLeft', 'alignCenter', 'alignRight', 'alignNone']],
                ['faSpin'],
                ['media', ['mediaPlugin', 'removePluginMedia']]
            ],
            document: [
                ['float', ['alignLeft', 'alignCenter', 'alignRight', 'alignNone']],
                ['media', ['mediaPlugin', 'removePluginMedia']]
            ],
            link: [
                ['link', ['linkPlugin', 'unlink']]
            ],
            table: [
                ['add', ['addRowDown', 'addRowUp', 'addColLeft', 'addColRight']],
                ['delete', ['deleteRow', 'deleteCol', 'deleteTable']]
            ],
        };

        options.callbacks = {
            onBlur: this._onBlurEditable.bind(this),
            onFocus: this._onFocusEditable.bind(this),
            onChange: this._onChange.bind(this),
            onImageUpload: this._onImageUpload.bind(this),
            onFocusnode: this._onFocusnode.bind(this),
        };

        options.isUnbreakableNode = function (node) {
            node = node && (node.tagName ? node : node.parentNode);
            if (!node) {
                return true;
            }
            return self.isUnbreakableNode(node);
        };
        options.isEditableNode = function (node) {
            node = node && (node.tagName ? node : node.parentNode);
            if (!node) {
                return false;
            }
            return self.isEditableNode(node);
        };
        options.displayPopover = this._isDisplayingPopover.bind(this);
        options.hasFocus = function () {
            return self._isFocused;
        };

        if (this.options.generateOptions) {
            this.options.generateOptions(options);
        }

        return options;
    },
    /**
     * @private
     * @returns {Object} modules list to load
     */
    _getPlugins: function () {
        return _.extend({}, wysiwygOptions.modules, modulesRegistry.plugins());
    },
    /**
     * Return an object describing the linked record.
     *
     * @private
     * @param {Object} options
     * @returns {Object} {res_id, res_model, xpath}
     */
    _getRecordInfo: function (options) {
        var data = this.options.recordInfo || {};
        if (typeof data === 'function') {
            data = data(options);
        }
        if (!data.context) {
            throw new Error("Context is missing");
        }
        return data;
    },
    /**
     * Return true if the editor is displaying the popover.
     *
     * @private
     * @param {Node} node
     * @returns {Boolean}
     */
    _isDisplayingPopover: function (node) {
        return true;
    },
    /**
     * Return true if the given node is in the editor.
     * Note: a button in the MediaDialog returns true.
     *
     * @private
     * @param {Node} node
     * @returns {Boolean}
     */
    _isEditorContent: function (node) {
        if (this.el === node) {
            return true;
        }
        if ($.contains(this.el, node)) {
            return true;
        }

        var children = this.getChildren();
        var allChildren = [];
        var child;
        while ((child = children.pop())) {
            allChildren.push(child);
            children = children.concat(child.getChildren());
        }

        var childrenDom = _.filter(_.unique(_.flatten(_.map(allChildren, function (obj) {
            return _.map(obj, function (value) {
                return value instanceof $ ? value.get() : value;
            });
        }))), function (node) {
            return node && node.DOCUMENT_NODE && node.tagName && node.tagName !== 'BODY' && node.tagName !== 'HTML';
        });
        return !!$(node).closest(childrenDom).length;
    },
    /**
     * Create an instance with the API lib.
     *
     * @private
     * @returns {$.Promise}
     */
    _loadInstance: function () {
        var defaultOptions = this._editorOptions();
        var summernoteOptions = _.extend({
            id: this.id,
        }, defaultOptions, _.omit(this.options, 'isEditableNode', 'isUnbreakableNode'));

        _.extend(summernoteOptions.callbacks, defaultOptions.callbacks, this.options.callbacks);
        if (this.options.keyMap) {
            _.defaults(summernoteOptions.keyMap.pc, defaultOptions.keyMap.pc);
            _.each(summernoteOptions.keyMap.pc, function (v, k, o) {
                if (!v) {
                    delete o[k];
                }
            });
            _.defaults(summernoteOptions.keyMap.mac, defaultOptions.keyMap.mac);
            _.each(summernoteOptions.keyMap.mac, function (v, k, o) {
                if (!v) {
                    delete o[k];
                }
            });
        }

        var plugins = _.extend(this._getPlugins(), this.options.plugins);
        summernoteOptions.modules = _.omit(plugins, function (v) {
            return !v;
        });

        if (this.$target.parent().length) {
            summernoteOptions.container = this.$target.parent().css('position', 'relative')[0];
        } else {
            summernoteOptions.container = this.$target[0].ownerDocument.body;
        }

        this.$target.summernote(summernoteOptions);

        this._summernote = this.$target.data('summernote');
        this._summernote.layoutInfo.editable.data('wysiwyg', this);
        this.$target.attr('data-wysiwyg-id', this.id).data('wysiwyg', this);
        $('.note-editor, .note-popover').not('[data-wysiwyg-id]').attr('data-wysiwyg-id', this.id);

        this.setElement(this._summernote.layoutInfo.editor);
        $(document).on('mousedown.' + this.id, this._onMouseDown.bind(this));
        $(document).on('mouseenter.' + this.id, '*', this._onMouseEnter.bind(this));
        $(document).on('mouseleave.' + this.id, '*', this._onMouseLeave.bind(this));
        $(document).on('mousemove.' + this.id, this._onMouseMove.bind(this));

        this.$el.removeClass('card');

        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * trigger_up 'wysiwyg_focus'.
     *
     * @private
     * @param {Object} [options]
     */
    _onFocus: function (options) {
        this.trigger_up('wysiwyg_focus', options);
    },
    /**
     * trigger_up 'wysiwyg_blur'.
     *
     * @private
     * @param {Object} [options]
     */
    _onBlur: function (options) {
        this.trigger_up('wysiwyg_blur', options);
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onMouseEnter: function (ev) {
        if (this._isFocused && !this._mouseInEditor && this._isEditorContent(ev.target)) {
            this._mouseInEditor = true;
        }
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onMouseLeave: function (ev) {
        if (this._isFocused && this._mouseInEditor) {
            this._mouseInEditor = null;
        }
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onMouseMove: function (ev) {
        if (this._mouseInEditor === null) {
            this._mouseInEditor = !!this._isEditorContent(ev.target);
        }
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onMouseDown: function (ev) {
        var self = this;
        if (this._isEditorContent(ev.target)) {
            setTimeout(function () {
                if (!self._editableHasFocus && !self._isEditorContent(document.activeElement)) {
                    self._summernote.layoutInfo.editable.focus();
                }
                if (!self._isFocused) {
                    self._isFocused = true;
                    self._onFocus();
                }
            });
        } else if (this._isFocused) {
            this._isFocused = false;
            this._onBlur();
        }
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onBlurEditable: function (ev) {
        var self = this;
        this._editableHasFocus = false;
        if (!this._isFocused) {
            return;
        }
        if (!this._justFocused && !this._mouseInEditor) {
            if (this._isFocused) {
                this._isFocused = false;
                this._onBlur();
            }
        } else if (!this._forceEditableFocus) {
            this._forceEditableFocus = true;
            setTimeout(function () {
                if (!self._isEditorContent(document.activeElement)) {
                    self._summernote.layoutInfo.editable.focus();
                }
                self._forceEditableFocus = false; // prevent stack size exceeded.
            });
        } else {
            this._mouseInEditor = null;
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onWysiwygBlur: function (ev) {
        if (ev.target === this) {
            return;
        }
        ev.stopPropagation();
        this._isFocused = false;
        this._forceEditableFocus = false;
        this._mouseInEditor = false;
        this._summernote.disable();
        this.$target.focus();
        setTimeout(this._summernote.enable.bind(this._summernote));
        this._onBlur(ev.data);
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onFocusEditable: function (ev) {
        var self = this;
        this._editableHasFocus = true;
        this._justFocused = true;
        setTimeout(function () {
            self._justFocused = false;
        });
    },
    /**
     * trigger_up 'wysiwyg_change'
     *
     * @private
     */
    _onChange: function () {
        var html = this._summernote.code();
        if (this.hints.length) {
            var hints = [];
            _.each(this.hints, function (hint) {
                if (html.indexOf('@' + hint.name) !== -1) {
                    hints.push(hint);
                }
            });
            this.hints = hints;
        }

        this._dirty = true;
        this.trigger_up('wysiwyg_change', {
            html: html,
            hints: this.hints,
            attachments: this.attachments,
        });
    },
    /**
     * trigger_up 'wysiwyg_attachment' when add an image found in the view.
     *
     * This method is called when an image is uploaded by the media dialog and returns the
     * object attachment as recorded in the "ir.attachment" model, via a wysiwyg_attachment event.
     *
     * For e.g. when sending email, this allows people to add attachments with the content
     * editor interface and that they appear in the attachment list.
     * The new documents being attached to the email, they will not be erased by the CRON
     * when closing the wizard.
     *
     * @private
     */
    _onImageUpload: function (attachments) {
        var self = this;
        attachments = _.filter(attachments, function (attachment) {
            return !_.findWhere(self.attachments, {
                id: attachment.id,
            });
        });
        if (!attachments.length) {
            return;
        }
        this.attachments = this.attachments.concat(attachments);

        // todo remove image not in the view

        this.trigger_up.bind(this, 'wysiwyg_attachment', this.attachments);
    },
    /**
     * Called when the carret focuses on another node (focus event, mouse event, or key arrow event)
     * from Unbreakable
     *
     * @private
     * @param {Node} node
     */
    _onFocusnode: function (node) {},
    /**
     * Do not override.
     *
     * @see _getRecordInfo
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {Object} ev.data.recordInfo
     * @param {Function(recordInfo)} ev.data.callback
     */
    _onGetRecordInfo: function (ev) {
        var data = this._getRecordInfo(ev.data);
        data.attachmentIDs = _.pluck(this.attachments, 'id');
        data.user_id = session.uid || session.user_id;
        ev.data.callback(data);
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
    var range = $.summernote.range.create();
    return range && {
        sc: range.sc,
        so: range.so,
        ec: range.ec,
        eo: range.eo,
    };
};
/**
 * @param {Node} startNode
 * @param {Number} startOffset
 * @param {Node} endNode
 * @param {Number} endOffset
 */
Wysiwyg.setRange = function (startNode, startOffset, endNode, endOffset) {
    $(startNode).focus();
    if (endNode) {
        $.summernote.range.create(startNode, startOffset, endNode, endOffset).select();
    } else {
        $.summernote.range.create(startNode, startOffset).select();
    }
    // trigger for Unbreakable
    $(startNode.tagName ? startNode : startNode.parentNode).trigger('wysiwyg.range');
};
/**
 * @param {Node} node - dom node
 * @param {Object} [options]
 * @param {Boolean} options.begin move the range to the beginning of the first node.
 * @param {Boolean} options.end move the range to the end of the last node.
 */
Wysiwyg.setRangeFromNode = function (node, options) {
    var last = node;
    while (last.lastChild) {
        last = last.lastChild;
    }
    var first = node;
    while (first.firstChild) {
        first = first.firstChild;
    }

    if (options && options.begin && !options.end) {
        Wysiwyg.setRange(first, 0);
    } else if (options && !options.begin && options.end) {
        Wysiwyg.setRange(last, last.textContent.length);
    } else {
        Wysiwyg.setRange(first, 0, last, last.tagName ? last.childNodes.length : last.textContent.length);
    }
};

//--------------------------------------------------------------------------
// jQuery extensions
//--------------------------------------------------------------------------

$.extend($.expr[':'], {
    o_editable: function (node, i, m) {
        while (node) {
            if (node.attributes) {
                var className = _.isString(node.className) && node.className || '';
                if (
                    className.indexOf('o_not_editable') !== -1 ||
                    (node.attributes.contenteditable &&
                        node.attributes.contenteditable.value !== 'true' &&
                        className.indexOf('o_fake_not_editable') === -1)
                ) {
                    return false;
                }
                if (
                    className.indexOf('o_editable') !== -1 ||
                    (node.attributes.contenteditable &&
                        node.attributes.contenteditable.value === 'true' &&
                        className.indexOf('o_fake_editable') === -1)
                ) {
                    return true;
                }
            }
            node = node.parentNode;
        }
        return false;
    },
});

return Wysiwyg;
});
