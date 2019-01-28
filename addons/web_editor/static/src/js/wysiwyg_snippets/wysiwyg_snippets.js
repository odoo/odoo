odoo.define('web_editor.wysiwyg.snippets', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg');
var snippetsEditor = require('web_editor.snippet.editor');

Wysiwyg.include({
    events: _.extend({}, Wysiwyg.prototype.events, {
        'content_changed .o_editable': '_onContentChange',
        'content_changed .note-editable': '_onContentChange',
    }),
    custom_events: _.extend({}, Wysiwyg.prototype.custom_events, {
        request_history_undo_record: '_onHistoryUndoRecordRequest',
        cover_will_change: '_onCoverWillChange',
        snippet_cloned: '_onSnippetCloned',
        snippet_dropped: '_onSnippetDropped',
        snippet_focused: '_onSnippetFocused',
    }),

    selectorEditableArea: '.note-editable',

    init: function (parent, options) {
        this._super.apply(this, arguments);

        options = _.clone(this.options);
        if (!options.snippets) {
            return;
        }
        if (options.snippets === true) {
            options.snippets = 'web_editor.snippets';
        }
        options.isUnbreakableNode = this.isUnbreakableNode.bind(this);
        options.isEditableNode = this.isEditableNode.bind(this);
        this.snippets = new snippetsEditor.Class(this, options);
    },
    /**
     * Preload snippets.
     *
     * @override
     **/
    willStart: function () {
        if (this.snippets) {
            this.snippets.loadSnippets(); // don't use the deferred
        }
        return this._super();
    },
    /**
     * Add options (snippets) to load snippet building block
     * snippets can by url begin with '/' or an view xml_id.
     *
     * @override
     * @param {string} [options.snippets]
     */
    start: function () {
        var self = this;
        return this._super().then(function () {
            if (!self.snippets) {
                return;
            }
            var $editable = $(self._summernote.layoutInfo.editable);
            self.snippets.setSelectorEditableArea(self.$el, self.selectorEditableArea);
            self.snippets.insertBefore(self.$el).then(function () {
                self.$el.before(self.snippets.$el);
                var $wrap = $('<div class="o_wrap_editable_snippets"/>');
                $wrap.on('scroll', function (event) {
                    self._summernote.triggerEvent('scroll', event);
                });
                var $contents = self.snippets.$el.siblings('#oe_manipulators')
                    .addClass('o_wysiwyg_to_remove').attr('contentEditable', false);
                $wrap.append($contents);
                $editable.before($wrap);
                $wrap.append($editable);
                setTimeout(function () { // add a set timeout for the transition
                    self.snippets.$el.addClass('o_loaded');
                    self.$el.addClass('o_snippets_loaded');
                    self.trigger_up('snippets_loaded', self.snippets.$el);
                });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isUnbreakableNode: function (node) {
        if (!this.snippets) {
            return this._super(node);
        }
        return this._super(node) || node.tagName === 'DIV' || snippetsEditor.globalSelector.is($(node));
    },
    /**
     * @override
     */
    isEditableNode: function (node) {
        if (!this._super(node)) {
            return false;
        }
        if (this.snippets && node.tagName === 'DIV' && !node.contentEditable) {
            if ($(node).parent('.row').length) {
                return true;
            }
            if (!_.find(node.childNodes, function (node) {
                var char = this.context.invoke('HelperPlugin.getRegex', 'char');
                return node.tagName !== 'DIV' && (node.tagName || node.textContent.match(char));
            })) {
                return false;
            }
        }
        return true;
    },
    /**
     * @override
     */
    save: function () {
        if (!this.snippets) {
            return this._super();
        }
        var defs = [];
        this.trigger_up('ready_to_save', {defs: defs});
        return $.when.apply($, defs)
            .then(this.snippets.cleanForSave.bind(this.snippets))
            .then(this._super.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onContentChange: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.snippets) {
            this.addHistoryStep();
        }
        this._onChange();
    },
    /**
     * @private
     * @override
     */
    _onChange: function () {
        if (this.snippets) {
            this.snippets.updateCurrentSnippetEditorOverlay();
        }
        this._summernote.invoke('toolbar.update', true);
        this._super.apply(this, arguments);
    },
    /**
     * Called when an element askes to record an history undo -> records it.
     *
     * @private
     */
    _onHistoryUndoRecordRequest: function () {
        this.addHistoryStep();
    },
    /**
     * Triggered when the user click on the snippet to drag&drop, remove or clone
     * (hide the popover)
     *
     * @private
     */
    _onCoverWillChange: function () {
        var context = this._summernote;
        var target = context.invoke('editor.restoreTarget', target);
        context.invoke('MediaPlugin.hidePopovers');
    },
    /**
     * Triggered when a snippet is cloned in the editable area
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {Object} ev.data.$target
     */
    _onSnippetCloned: function (ev) {
        this._summernote.invoke('UnbreakablePlugin.secureArea', ev.data.$target[0]);
    },
    /**
     * Triggered when a snippet is dropped in the editable area
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {Object} ev.data.$target
     */
    _onSnippetDropped: function (ev) {
        this._summernote.invoke('UnbreakablePlugin.secureArea', ev.data.$target[0]);
    },
    /**
     * Triggered when the user focuses on a snippet: hides the popover.
     *
     * @private
     */
    _onSnippetFocused: function () {
        var context = this._summernote;
        var target = context.invoke('editor.restoreTarget', target);
        context.invoke('MediaPlugin.hidePopovers');
        context.invoke('MediaPlugin.update', target);
    },
});

//--------------------------------------------------------------------------
// jQuery extensions
//--------------------------------------------------------------------------

$.fn.extend({
    /**
     * Set the range and focus at the start of the first found node.
     *
     * @returns {JQuery}
     */
    focusIn: function () {
        if (this.length) {
            Wysiwyg.setRangeFromNode(this[0], {begin: true});
            $(this).trigger('mouseup');
        }
        return this;
    },
    /**
     * Set the range and focus at the end of the first found node.
     *
     * @returns {JQuery}
     */
    focusInEnd: function () {
        if (this.length) {
            Wysiwyg.setRangeFromNode(this[0], {end: true});
            $(this).trigger('mouseup');
        }
        return this;
    },
    /**
     * Set the range and focus on a selection, accounting for zero-width spaces.
     *
     * @returns {JQuery}
     */
    selectContent: function () {
        if (this.length) {
            Wysiwyg.setRangeFromNode(this[0]);
            var range = $.summernote.range.create();
            if (!range.sc.tagName && range.so === 0 && range.sc.textContent[range.so] === '\u200B') {
                range.so += 1;
            }
            if (!range.ec.tagName && range.eo === range.ec.textContent.length && range.ec.textContent[range.eo - 1] === '\u200B') {
                range.eo -= 1;
            }
            range.select();
            $(this).trigger('mouseup');
        }
        return this;
    },
});

});
