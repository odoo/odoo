odoo.define('web_editor.wysiwyg', function (require) {
'use strict';
var Widget = require('web.Widget');
var SummernoteManager = require('web_editor.rte.summernote');
var summernoteCustomColors = require('web_editor.rte.summernote_custom_colors');
var id = 0;

// core.bus
// media_dialog_demand
var Wysiwyg = Widget.extend({
    xmlDependencies: [
    ],
    defaultOptions: {
        'focus': false,
        'toolbar': [
            ['style', ['style']],
            ['font', ['bold', 'italic', 'underline', 'clear']],
            ['fontsize', ['fontsize']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['table', ['table']],
            ['insert', ['link', 'picture']],
            ['history', ['undo', 'redo']],
        ],
        'styleWithSpan': false,
        'inlinemedia': ['p'],
        'lang': 'odoo',
        'colors': summernoteCustomColors,
        recordInfo: {
            context: {},
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
        this.id = ++id;
        this.options = options;
    },
    /**
     * Load assets and color picker template then call summernote API
     * and replace $el by the summernote editable node.
     *
     * @override
     **/
    willStart: function () {
        this._summernoteManager = new SummernoteManager(this);
        this.$target = this.$el;
        return this._super();
    },
    /**
     *
     * @override
     */
    start: function () {
        this.$target.wrap('<odoo-wysiwyg-container>');
        this.$el = this.$target.parent();
        var options = this._editorOptions();
        this.$target.summernote(options);
        this.$editor = this.$('.note-editable:first');
        this.$editor.data('wysiwyg', this);
        this.$editor.data('oe-model', options.recordInfo.res_model);
        this.$editor.data('oe-id', options.recordInfo.res_id);
        $(document).on('mousedown', this._blur);
        this._value = this.$target.html() || this.$target.val();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        $(document).off('mousedown', this._blur);
        if (this.$target && this.$target.is('textarea') && this.$target.next('.note-editor').length) {
            this.$target.summernote('destroy');
        }
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
    isDirty: function () {
        return this._value !== (this.$editor.html() || this.$editor.val());
    },
    /**
     * Set the focus on the element.
     */
    focus: function () {
        console.log('focus');
    },
    /**
     * Get the value of the editable element.
     *
     * @param {object} [options]
     * @param {jQueryElement} [options.$layout]
     * @returns {String}
     */
    getValue: function (options) {
        var $editable = options && options.$layout || this.$editor.clone();
        $editable.find('[contenteditable]').removeAttr('contenteditable');
        $editable.find('[class=""]').removeAttr('class');
        $editable.find('[style=""]').removeAttr('style');
        $editable.find('[title=""]').removeAttr('title');
        $editable.find('[alt=""]').removeAttr('alt');
        $editable.find('[data-original-title=""]').removeAttr('data-original-title');
        $editable.find('a.o_image, span.fa, i.fa').html('');
        $editable.find('[aria-describedby]').removeAttr('aria-describedby').removeAttr('data-original-title');
        return $editable.html();
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
     * Create/Update cropped attachments.
     *
     * @param {jQuery} $editable
     * @returns {Promise}
     */
    saveModifiedImages: function ($editable) {
        return this._summernoteManager.saveModifiedImages($editable);
    },
    /**
     * @param {String} value
     * @param {Object} options
     * @param {Boolean} [options.notifyChange]
     * @returns {String}
     */
    setValue: function (value, options) {
        if (this.$editor.is('textarea')) {
            this.$target.val(value);
        } else {
            this.$target.html(value);
        }
        this.$editor.html(value);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _editorOptions: function () {
        var self = this;
        var options = Object.assign({}, $.summernote.options, this.defaultOptions, this.options);
        if (this.options.generateOptions) {
            options = this.options.generateOptions(options);
        }
        options.airPopover = options.toolbar;
        options.onChange = function (html, $editable) {
            $editable.trigger('content_changed');
            self.trigger_up('wysiwyg_change');
        };
        options.onUpload = function (attachments) {
            self.trigger_up('wysiwyg_attachment', attachments);
        };
        options.onFocus = function () {
            self.trigger_up('wysiwyg_focus');
        };
        options.onBlur = function () {
            self.trigger_up('wysiwyg_blur');
        };
        return options;
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
    var range = $.summernote.core.range.create();
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
        $.summernote.core.range.create(startNode, startOffset, endNode, endOffset).select();
    } else {
        $.summernote.core.range.create(startNode, startOffset).select();
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
return Wysiwyg;
});
odoo.define('web_editor.widget', function (require) {
'use strict';
    return {
        Dialog: require('wysiwyg.widgets.Dialog'),
        MediaDialog: require('wysiwyg.widgets.MediaDialog'),
        LinkDialog: require('wysiwyg.widgets.LinkDialog'),
    };
});
