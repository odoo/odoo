odoo.define('note.systray', function (require) {
"use strict";

var core = require('web.core');
var ActivityMenu = require('mail.systray').ActivityMenu;
var datepicker = require('web.datepicker');

var _t = core._t;

ActivityMenu.include({
    events: _.extend({}, ActivityMenu.prototype.events, {
        'click .o_note_show': '_onAddNoteClick',
        'click .o_note_save': '_onNoteSaveClick',
        'click .o_note_set_datetime': '_onNoteDateTimeSetClick',
        'keydown input.o_note_input': '_onNoteInputKeyDown',
        'click .o_note': '_onNewNoteClick',
    }),
    //--------------------------------------------------
    // Private
    //--------------------------------------------------
    /**
     * Moving notes at first place in activities list
     * @override
     */
    _getActivityData: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var noteIndex = _.findIndex(self.activities, function (val) { return val.model === 'note.note'; });
            if (noteIndex > 0) {
                self.activities.splice(0, 0, self.activities.splice(noteIndex, 1)[0]);
            }
        });
    },
    /**
     * Save the note to database using datepicker date and input text as note
     * @private
     */
    _saveNote: function () {
        var note = this.$('.o_note_input').val().trim();
        if (! note) {
            return;
        }
        var params = {'note': note};
        var noteDateTime = this.noteDateTimeWidget.getValue();
        if (noteDateTime) {
            params = _.extend(params, {'date_deadline': noteDateTime});
        }
        this.$('.o_note_show').removeClass('hidden');
        this.$('.o_note').addClass('hidden');
        this._rpc({
            model: 'note.note',
            method: 'quick_create_note',
            args: [[], params.note, params.date_deadline || false],
        }).then(this._updateActivityPreview.bind(this));
    },
    //-----------------------------------------
    // Handlers
    //-----------------------------------------
    /**
     * @override
     */
    _onActivityFilterClick: function (ev) {
        var $el = $(ev.currentTarget);
        if (!$el.hasClass("o_note")) {
            var data = _.extend({}, $el.data(), $(ev.target).data());
            if (data.res_model === "note.note" && data.filter === "my") {
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: _t('Notes'),
                    res_model:  data.res_model,
                    views: [[false, 'kanban'], [false, 'form'], [false, 'list']],
                    context: {
                        search_default_open_true: true
                    }
                });
            } else {
                this._super.apply(this, arguments);
            }
        }
    },
    /**
     * When add new note button clicked, toggling quick note input
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddNoteClick: function (ev) {
        ev.stopPropagation();
        if (!this.noteDateTimeWidget){
            this.noteDateTimeWidget = new datepicker.DateWidget(this, {useCurrent: true});
        }
        this.noteDateTimeWidget.appendTo(this.$('.o_note_datetime'));
        this.noteDateTimeWidget.$input.attr('placeholder', _t("Today"));
        this.$('.o_note_show, .o_note').toggleClass('hidden');
        this.$('.o_note_input').val('').focus();
      
    },
    /**
     * Systerm tray must be open while focusing/clicking on input of new quick
     * add note form. This Preventing systerm tray from closing.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onNewNoteClick: function (ev) {
        ev.stopPropagation();
    },
    /**
     * Opens datetime picker for note.
     * Quick FIX due to no option for set custom icon instead of caret in datepicker.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onNoteDateTimeSetClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.noteDateTimeWidget.$input.click();
    },
    /**
     * Saving note (quick create) and updating activity preview
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onNoteSaveClick: function (ev) {
        this._saveNote();
    },
    /**
     * Handling Enter key for quick create note.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onNoteInputKeyDown: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            this._saveNote();
        }
    },
});
});
