odoo.define('web_editor.editor', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var core = require('web.core');
var rte = require('web_editor.rte');
var snippetsEditor = require('web_editor.snippet.editor');
var summernoteCustomColors = require('web_editor.rte.summernote_custom_colors');

var _t = core._t;

var EditorMenuBar = Widget.extend({
    template: 'web_editor.editorbar',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events: {
        'click button[data-action=save]': '_onSaveClick',
        'click button[data-action=cancel]': '_onCancelClick',
    },
    custom_events: {
        request_editable: '_onRequestEditable',
        request_history_undo_record: '_onHistoryUndoRecordRequest',
        request_save: '_onSaveRequest',
    },

    /**
     * Initializes RTE and snippets menu.
     *
     * @constructor
     */
    init: function (parent, options) {
        var self = this;
        var res = this._super.apply(this, arguments);
        var Editor = options.Editor || rte.Class;
        this.rte = new Editor(this, {
            getConfig: function ($editable) {
                var param = self._getDefaultConfig($editable);
                if (options.generateOptions) {
                    param = options.generateOptions(param);
                }
                return param;
            },
            saveElement: options.saveElement,
        });
        this.rte.on('rte:start', this, function () {
            self.trigger('rte:start');
        });

        // Snippets edition
        var $editable = this.rte.editable();
        window.__EditorMenuBar_$editable = $editable; // TODO remove this hack asap

        if (options.snippets) {
            this.snippetsMenu = new snippetsEditor.Class(this, Object.assign({
                $el: $editable,
                selectorEditableArea: '.o_editable',
            }, options));
        }

        return res;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];

        core.bus.on('editor_save_request', this, this.save);
        core.bus.on('editor_discard_request', this, this.cancel);

        $('.dropdown-toggle').dropdown();

        $(document).on('keyup', function (event) {
            if ((event.keyCode === 8 || event.keyCode === 46)) {
                var $target = $(event.target).closest('.o_editable');
                if (!$target.is(':has(*:not(p):not(br))') && !$target.text().match(/\S/)) {
                    $target.empty();
                }
            }
        });
        $(document).on('click', '.note-editable', function (ev) {
            ev.preventDefault();
        });
        $(document).on('submit', '.note-editable form .btn', function (ev) {
            ev.preventDefault(); // Disable form submition in editable mode
        });
        $(document).on('hide.bs.dropdown', '.dropdown', function (ev) {
            // Prevent dropdown closing when a contenteditable children is focused
            if (ev.originalEvent
                    && $(ev.target).has(ev.originalEvent.target).length
                    && $(ev.originalEvent.target).is('[contenteditable]')) {
                ev.preventDefault();
            }
        });

        this.rte.start();

        var flag = false;
        window.onbeforeunload = function (event) {
            if (rte.history.getEditableHasUndo().length && !flag) {
                flag = true;
                _.defer(function () { flag=false; });
                return _t('This document is not saved!');
            }
        };

        // Snippets menu
        if (self.snippetsMenu) {
            defs.push(this.snippetsMenu.insertAfter(this.$el));
        }
        this.rte.editable().find('*').off('mousedown mouseup click');

        return Promise.all(defs).then(function () {
            self.trigger_up('edit_mode');
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        core.bus.off('editor_save_request', this, this._onSaveRequest);
        core.bus.off('editor_discard_request', this, this._onDiscardRequest);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Asks the user if he really wants to discard its changes (if there are
     * some of them), then simply reload the page if he wants to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded when the user answers yes
     *        (do nothing otherwise but add this to allow class extension)
     * @returns {Promise}
     */
    cancel: function (reload) {
        var self = this;
        return new Promise(function(resolve, reject) {
            if (!rte.history.getEditableHasUndo().length) {
                resolve();
            } else {
                var confirm = Dialog.confirm(this, _t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."), {
                    confirm_callback: resolve,
                });
                confirm.on('closed', self, reject);
            }
        }).then(function () {
            if (reload !== false) {
                window.onbeforeunload = null;
                return self._reload();
            }
        });
    },
    /**
     * Asks the snippets to clean themself, then saves the page, then reloads it
     * if asked to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded after the save
     * @returns {Promise}
     */
    save: async function (reload) {
        var defs = [];
        this.trigger_up('ready_to_save', {defs: defs});
        await Promise.all(defs);

        if (this.snippetsMenu) {
            await this.snippetsMenu.cleanForSave();
        }
        await this.getParent().saveModifiedImages(this.rte.editable());
        await this.rte.save();

        if (reload !== false) {
            return this._reload();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getDefaultConfig: function ($editable) {
        return {
            'airMode' : true,
            'focus': false,
            'airPopover': [
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
            'inlinemedia' : ['p'],
            'lang': 'odoo',
            'onChange': function (html, $editable) {
                $editable.trigger('content_changed');
            },
            'colors': summernoteCustomColors,
        };
    },
    /**
     * Reloads the page in non-editable mode, with the right scrolling.
     *
     * @private
     * @returns {Promise} (never resolved, the page is reloading anyway)
     */
    _reload: function () {
        window.location.hash = 'scrollTop=' + window.document.body.scrollTop;
        if (window.location.search.indexOf('enable_editor') >= 0) {
            window.location.href = window.location.href.replace(/&?enable_editor(=[^&]*)?/g, '');
        } else {
            window.location.reload(true);
        }
        return new Promise(function(){});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "Discard" button is clicked -> discards the changes.
     *
     * @private
     */
    _onCancelClick: function () {
        this.cancel();
    },
    /**
     * Called when an element askes to record an history undo -> records it.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onHistoryUndoRecordRequest: function (ev) {
        this.rte.historyRecordUndo(ev.data.$target, ev.data.event);
    },
    /**
     * Called when the "Save" button is clicked -> saves the changes.
     *
     * @private
     */
    _onSaveClick: function () {
        this.save();
    },
    /**
     * Called when a discard request is received -> discard the page content
     * changes.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDiscardRequest: function (ev) {
        this.cancel(ev.data.reload).then(ev.data.onSuccess, ev.data.onFailure);
    },
    /**
     * Called when a save request is received -> saves the page content.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveRequest: function (ev) {
        ev.stopPropagation();
        this.save(ev.data.reload).then(ev.data.onSuccess, ev.data.onFailure);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onRequestEditable: function (ev) {
        ev.data.callback(this.rte.editable());
    },
});

return {
    Class: EditorMenuBar,
};
});
