/** @odoo-module **/

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";

export class CalendarQuickCreate extends Component {
    setup() {
        this.titleRef = useAutofocus({ refName: "title" });
        this.notification = useService("notification");
        this.creatingRecord = false;
    }

    get dialogTitle() {
        return _t("New Event");
    }

    get recordTitle() {
        return this.titleRef.el.value.trim();
    }
    get record() {
        return {
            ...this.props.record,
            title: this.recordTitle,
        };
    }

    editRecord() {
        this.props.editRecord(this.record);
        this.props.close();
    }
    async createRecord() {
        if (this.creatingRecord) {
            return;
        }

        if (this.recordTitle) {
            try {
                this.creatingRecord = true;
                await this.props.model.createRecord(this.record);
                this.props.close();
            } catch {
                this.editRecord();
            }
        } else {
            this.titleRef.el.classList.add("o_field_invalid");
            this.notification.add(_t("Meeting Subject"), {
                title: _t("Invalid fields"),
                type: "danger",
            });
        }
    }

    onInputKeyup(ev) {
        switch (ev.key) {
            case "Enter":
                this.createRecord();
                break;
            case "Escape":
                this.props.close();
                break;
        }
    }
    onCreateBtnClick() {
        this.createRecord();
    }
    onEditBtnClick() {
        this.editRecord();
    }
    onCancelBtnClick() {
        this.props.close();
    }
}

CalendarQuickCreate.template = "web.CalendarQuickCreate";
CalendarQuickCreate.components = {
    Dialog,
};
CalendarQuickCreate.props = {
    title: { type: String, optional: true },
    close: Function,
    record: Object,
    model: Object,
    editRecord: Function,
};
