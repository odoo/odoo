/** @odoo-module */

import { ActivityMenu } from "@mail/web/activity/activity_menu";
import { patch } from "@web/core/utils/patch";
import { useRef, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DatePicker } from "@web/core/datepicker/datepicker";
import { onExternalClick } from "@mail/utils/hooks";

patch(ActivityMenu.prototype, "note", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
        this.state = useState({ addingNote: false, addingNoteDate: false });
        this.noteInputRef = useRef("noteInput");
        useEffect(
            (addingNote) => {
                if (addingNote) {
                    this.noteInputRef.el.focus();
                }
            },
            () => [this.state.addingNote]
        );
        onExternalClick("noteInput", (ev) => {
            if (
                ev.target.closest(".o-mail-ActivityMenu-show") ||
                ev.target.closest(".bootstrap-datetimepicker-widget")
            ) {
                return;
            }
            this.state.addingNote = false;
        });
    },

    sortActivityGroups() {
        this._super();
        this.store.activityGroups.sort((g1, g2) => {
            if (g1.model === "note.note" ? true : false) {
                return -1;
            }
            if (g2.model === "note.note" ? true : false) {
                return 1;
            }
        });
    },

    onKeydownNoteInput(ev) {
        if (ev.key === "Enter") {
            this.saveNote();
        }
    },

    async saveNote() {
        const { DateTime } = luxon;
        const urlRegExp = /http(s)?:\/\/(www\.)?[a-zA-Z0-9@:%_+~#=~#?&/=\-;!.]{3,2000}/g;
        const note = this.noteInputRef.el.value.replace(urlRegExp, '<a href="$&">$&</a>').trim();
        if (!note) {
            return;
        }
        await this.rpc("/note/new", {
            note: note,
            date_deadline: this.state.addingNoteDate ? this.state.addingNoteDate : DateTime.local(),
        });
        this.state.addingNote = false;
        this.fetchSystrayActivities();
    },
});

ActivityMenu.components = {
    ...ActivityMenu.components,
    DatePicker,
};
