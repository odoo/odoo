import { useAutofocus, useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

import { Component, signal } from "@odoo/owl";

export class CalendarQuickCreate extends Component {
    static template = "web.CalendarQuickCreate";
    static components = {
        Dialog,
    };
    static props = {
        title: { type: String, optional: true },
        close: Function,
        record: Object,
        model: Object,
        editRecord: Function,
    };

    titleRef = signal(null);

    setup() {
        useAutofocus({ ref: this.titleRef });
        this.notification = useService("notification");
        this.creatingRecord = false;
    }

    get dialogTitle() {
        return _t("New Event");
    }

    get recordTitle() {
        return this.titleRef().value.trim();
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
            this.titleRef().classList.add("o_field_invalid");
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
