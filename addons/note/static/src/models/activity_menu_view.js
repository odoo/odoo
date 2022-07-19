/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import '@mail/models/activity_menu_view'; // ensure the model definition is loaded before the patch

const { DateTime } = luxon;

addRecordMethods('ActivityMenuView', {
    /**
     * @param {MouseEvent} ev
     */
    onClickAddNote(ev) {
        this.update({
            addingNoteDoFocus: true,
            isAddingNote: true,
        });
    },
    /**
     * @param {MouseEvent} ev
     */
    onClickSaveNote(ev) {
        this.saveNote();
    },
    onComponentUpdate() {
        if (this.addingNoteDoFocus && this.noteInputRef.el) {
            this.noteInputRef.el.focus();
            this.update({ addingNoteDoFocus: clear() });
        }
    },
    /**
     * @param {DateTime|string} date
     */
    onDateTimeChanged(date) {
        this.update({ addingNoteDate: date ? date : clear() });
    },
    /**
     * @param {KeyboardEvent} ev
     */
    onKeydownNoteInput(ev) {
        if (ev.key === 'Enter') {
            this.saveNote();
        }
    },
    async saveNote() {
        const note = this.noteInputRef.el.value.trim();
        if (!note) {
            return;
        }
        this.update({ isAddingNote: false });
        await this.messaging.rpc({
            route: '/note/new',
            params: {
                'note': note,
                'date_deadline': this.addingNoteDate ? this.addingNoteDate : new DateTime.local(),
            },
        });
        this.fetchData();
    },
    /**
     * @private
     * @returns {string}
     */
    _computeAddingNoteDatePlaceholder() {
        return this.env._t("Today");
    },
});

patchRecordMethods('ActivityMenuView', {
    /**
     * @override
     */
    close() {
        this.update({
            addingNoteDoFocus: clear(),
            isAddingNote: false,
        });
        this._super();
    },
    /**
     * @override
     */
    _onClickCaptureGlobal(ev) {
        if (ev.target.closest('.bootstrap-datetimepicker-widget')) {
            return;
        }
        this._super(ev);
    },
    /**
     * @override
     */
    _sortActivityGroups(ev) {
        const res = this._super();
        res.unshift(['truthy-first', 'isNote']);
        return res;
    },
});

addFields('ActivityMenuView', {
    addingNoteDate: attr(),
    addingNoteDoFocus: attr({
        default: false,
    }),
    addingNoteDatePlaceholder: attr({
        compute: '_computeAddingNoteDatePlaceholder',
    }),
    isAddingNote: attr({
        default: false,
    }),
    noteInputRef: attr(),
});
