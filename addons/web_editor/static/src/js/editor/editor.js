odoo.define('web_editor.editor', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var core = require('web.core');
var rte = require('web_editor.rte');
var snippetsEditor = require('web_editor.snippet.editor');

var _t = core._t;

var EditorMenuBar = Widget.extend({
    template: 'web_editor.editorbar',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events: {
        'click button[data-action=save]': '_onSaveClick',
        'click button[data-action=cancel]': '_onCancelClick',
    },
    custom_events: {
        request_history_undo_record: '_onHistoryUndoRecordRequest',
        request_save: '_onSaveRequest',
    },

    /**
     * Initializes RTE and snippets menu.
     *
     * @constructor
     */
    init: function (parent) {
        var self = this;
        var res = this._super.apply(this, arguments);
        this.rte = new rte.Class(this);
        this.rte.on('rte:start', this, function () {
            self.trigger('rte:start');
        });

        // Snippets edition
        var $editable = this.rte.editable();
        window.__EditorMenuBar_$editable = $editable; // TODO remove this hack asap
        this.snippetsMenu = new snippetsEditor.Class(this, $editable);

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
        defs.push(this.snippetsMenu.insertAfter(this.$el));
        this.rte.editable().find('*').off('mousedown mouseup click');

        return $.when.apply($, defs).then(function () {
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
     * @returns {Deferred}
     */
    cancel: function (reload) {
        var self = this;
        var def = $.Deferred();
        if (!rte.history.getEditableHasUndo().length) {
            def.resolve();
        } else {
            var confirm = Dialog.confirm(this, _t("If you discard the current edition, all unsaved changes will be lost. You can cancel to return to the edition mode."), {
                confirm_callback: def.resolve.bind(def),
            });
            confirm.on('closed', def, def.reject);
        }
        return def.then(function () {
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
     * @returns {Deferred}
     */
    save: function (reload) {
        var self = this;
        var defs = [];
        this.trigger_up('ready_to_save', {defs: defs});
        return $.when.apply($, defs).then(function () {
            self.snippetsMenu.cleanForSave();
            return self._saveCroppedImages();
        }).then(function () {
            return self.rte.save();
        }).then(function () {
            if (reload !== false) {
                return self._reload();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Reloads the page in non-editable mode, with the right scrolling.
     *
     * @private
     * @returns {Deferred} (never resolved, the page is reloading anyway)
     */
    _reload: function () {
        window.location.hash = 'scrollTop=' + window.document.body.scrollTop;
        if (window.location.search.indexOf('enable_editor') >= 0) {
            window.location.href = window.location.href.replace(/&?enable_editor(=[^&]*)?/g, '');
        } else {
            window.location.reload(true);
        }
        return $.Deferred();
    },
    /**
     * @private
     */
    _saveCroppedImages: function () {
        var self = this;
        var defs = _.map(this.rte.editable().find('.o_cropped_img_to_save'), function (croppedImg) {
            var $croppedImg = $(croppedImg);
            $croppedImg.removeClass('o_cropped_img_to_save');

            var resModel = $croppedImg.data('crop:resModel');
            var resID = $croppedImg.data('crop:resID');
            var cropID = $croppedImg.data('crop:id');
            var mimetype = $croppedImg.data('crop:mimetype');
            var originalSrc = $croppedImg.data('crop:originalSrc');

            var datas = $croppedImg.attr('src').split(',')[1];

            if (!cropID) {
                var name = originalSrc + '.crop';
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'create',
                    args: [{
                        res_model: resModel,
                        res_id: resID,
                        name: name,
                        datas_fname: name,
                        datas: datas,
                        mimetype: mimetype,
                        url: originalSrc, // To save the original image that was cropped
                    }],
                }).then(function (attachmentID) {
                    return self._rpc({
                        model: 'ir.attachment',
                        method: 'generate_access_token',
                        args: [[attachmentID]],
                    }).then(function (access_token) {
                        $croppedImg.attr('src', '/web/image/' + attachmentID + '?access_token=' + access_token[0]);
                    });
                });
            } else {
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'write',
                    args: [[cropID], {datas: datas}],
                });
            }
        });
        return $.when.apply($, defs);
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
});

return {
    Class: EditorMenuBar,
};
});
