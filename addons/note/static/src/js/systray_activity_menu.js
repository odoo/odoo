odoo.define('note.systray.ActivityMenu', function (require) {
"use strict";

var ActivityMenu = require('mail.systray.ActivityMenu');

var core = require('web.core');
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
     * Moving notes at first place
     * @override
     */
    _getActivityData: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var reminderIndex = _.findIndex(self.activities, function (val) {
                return val.model === 'note.note';
            });
            if (reminderIndex > 0) {
                self.activities.splice(0, 0, self.activities.splice(reminderIndex, 1)[0]);
            }
        });
    },
    /**
     * Save the note to database using datepicker date and field as note
     * By default, when no datetime is set, it uses the current datetime.
     *
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
        } else {
            params = _.extend(params, {'date_deadline': moment()});
        }
        this.$('.o_note_show').removeClass('d-none');
        this.$('.o_note').addClass('d-none');
        this._rpc({
            route: '/note/new',
            params: params,
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
                    name: data.model_name,
                    res_model:  data.res_model,
                    views: [[false, 'kanban'], [false, 'form'], [false, 'list']]
                });
            } else {
                this._super.apply(this, arguments);
            }
        }
    },
    /**
     * When add new note button clicked, toggling quick note create view inside
     * Systray activity view
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
        this.$('.o_note_show, .o_note').toggleClass('d-none');
        this.$('.o_note_input').val('').focus();
    },
    /**
     * When focusing on input for new quick note systerm tray must be open.
     * Preventing to close
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
        this.noteDateTimeWidget.$input.select();
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
