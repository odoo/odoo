/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus, useService } from "@web/core/utils/hooks";

import { Component, useRef } from "@odoo/owl";

export class AccountReportFootnoteDialog extends Component {
    static template = "account_reports.AccountReportFootnoteDialog";
    static components = { Dialog };

    setup() {
        this.orm = useService("orm");

        this.title = _t("Annotate");
        this.text = useRef("text");
        this.needRefresh = false;

        useAutofocus({refName: "text"});
    }

    async _save() {
        const hasFootnote = this.props.footnoteID;
        const hasText = this.text.el.value.length > 0;

        if (!hasFootnote && hasText)
            await this._create();
        else if (hasFootnote && hasText)
            await this._update();
        else if (hasFootnote && !hasText)
            await this._delete();

        if (this.needRefresh)
            await this.props.refresh();

        this.props.close();
    }

    _cancel() {
        this.props.close();
    }

    async _create() {
        await this.orm.call(
            "account.report.footnote",
            "create",
            [
                {
                    report_id: this.props.reportID,
                    line_id: this.props.lineID,
                    text: this.text.el.value,
                },
            ],
            {
                context: this.props.context,
            },
        );

        this.needRefresh = true;
    }

    async _update() {
        await this.orm.call(
            "account.report.footnote",
            "write",
            [
                this.props.footnoteID,
                {
                    text: this.text.el.value,
                },
            ],
            {
                context: this.props.context,
            }
        );

        this.needRefresh = true;
    }

    async _delete() {
        await this.orm.call(
            "account.report.footnote",
            "unlink",
            [
                this.props.footnoteID,
            ],
            {
                context: this.props.context,
            },
        );

        this.needRefresh = true;
    }
}
