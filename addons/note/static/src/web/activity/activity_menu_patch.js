/** @odoo-module */

import { onExternalClick } from "@mail/utils/hooks";
import { ActivityMenu } from "@mail/web/activity/activity_menu";
import { useEffect, useRef, useState } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, "note", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
        this.state = useState({ addingNote: false });
        this.noteInputRef = useRef("noteInput");
        this.addingNoteDate = false;
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
                ev.target.closest(".o_datetime_picker")
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
            date_deadline: this.addingNoteDate ? this.addingNoteDate : DateTime.local(),
        });
        this.state.addingNote = false;
        this.fetchSystrayActivities();
    },
});

ActivityMenu.components = {
    ...ActivityMenu.components,
    DateTimeInput,
};
