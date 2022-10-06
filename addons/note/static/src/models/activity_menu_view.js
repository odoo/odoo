/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

const { DateTime } = luxon;

registerPatch({
    name: 'ActivityMenuView',
    recordMethods: {
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
         * @override
         */
        _onClickCaptureGlobal(ev) {
            if (ev.target.closest('.bootstrap-datetimepicker-widget')) {
                return;
            }
            this._super(ev);
        },
    },
    fields: {
        activityGroups: {
            sort() {
                return [
                    ['truthy-first', 'isNote'],
                    ...this._super,
                ];
            },
        },
        addingNoteDate: attr(),
        addingNoteDatePlaceholder: attr({
            compute() {
                return this.env._t("Today");
            },
        }),
        addingNoteDoFocus: attr({
            default: false,
        }),
        isAddingNote: attr({
            default: false,
        }),
        noteInputRef: attr(),
    },
});
