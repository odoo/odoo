import { Component, useState, useRef, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { serializeDate } from "@web/core/l10n/dates";
import { AnnotationPopoverLine } from "@account_reports/components/account_report/line_name/popover_line/annotation_popover_line";
import { removeTaxGroupingFromLineId } from "@account_reports/js/util";

const { DateTime } = luxon;

export class AccountReportAnnotationsPopover extends Component {
    static template = "account_reports.AccountReportAnnotationsPopover";
    static props = {
        controller: Object,
        lineName: Object,
        lineID: String,
        close: { type: Function, optional: true },
        isAddingAnnotation: { type: Boolean, optional: true },
    };
    static components = {
        DateTimeInput,
        AnnotationPopoverLine,
    };

    setup() {
        this.notificationService = useService("notification");

        this.newAnnotation = useState({
            value: this.props.isAddingAnnotation ? this._getNewAnnotation() : {},
        });

        this.annotations = useState(this.props.controller.visibleAnnotations[removeTaxGroupingFromLineId(this.props.lineID)]);

        this.popoverTable = useRef("popoverTable");
        this.currentPromise = null;

        onWillDestroy(async () => {
            if (this.currentPromise) {
                await this.currentPromise;
            }
        });
    }

    get isAddingAnnotation() {
        return Object.keys(this.newAnnotation.value).length !== 0;
    }

    async refreshAnnotations() {
        this.currentPromise = null;
        await this.props.controller.refreshAnnotations();
        this.annotations = this.props.controller.visibleAnnotations[removeTaxGroupingFromLineId(this.props.lineID)];
        if (this.isAddingAnnotation) {
            this.cleanNewAnnotation();
        }
    }

    _getNewAnnotation() {
        const date =
            this.props.controller.options.date.filter === "today"
                ? new Date().toISOString().split("T")[0]
                : this.props.controller.options.date.date_to;
        return {
            date: DateTime.fromISO(date),
            text: "",
            lineID: this.props.lineID,
        };
    }

    cleanNewAnnotation() {
        this.newAnnotation.value = {};
    }

    addAnnotation() {
        this.newAnnotation.value = this._getNewAnnotation();
    }

    formatAnnotation(annotation) {
        return {
            id: annotation.id,
            date: annotation.date ? DateTime.fromISO(annotation.date) : null,
            text: annotation.text,
            lineID: annotation.line_id,
        };
    }

    async saveNewAnnotation(newAnnotation) {
        if (newAnnotation.text) {
            this.currentPromise = this.env.services.orm.call(
                "account.report.annotation",
                "create",
                [
                    {
                        report_id: this.props.controller.options.report_id,
                        line_id: newAnnotation.lineID,
                        text: newAnnotation.text,
                        date: newAnnotation.date ? serializeDate(newAnnotation.date) : null,
                        fiscal_position_id: this.props.controller.options.fiscal_position,
                    },
                ],
                {
                    context: this.props.context,
                }
            );
            // We're using a .then() here to make sure that even if the component is destroyed
            // we'll call the function to finalize the logic.
            this.currentPromise.then(async () => {
                await this.refreshAnnotations();
                if (this.popoverTable.el) {
                    this.popoverTable.el.scrollIntoView({ behavior: "smooth", block: "end" });
                }
            });
        }
    }

    async deleteAnnotation(annotationId) {
        this.currentPromise = this.env.services.orm.call(
            "account.report.annotation",
            "unlink",
            [annotationId],
            { context: this.props.controller.context }
        );
        await this.currentPromise;
        await this.refreshAnnotations();
    }

    async editAnnotation(editedAnnotation, existingAnnotation) {
        this.currentPromise = this.env.services.orm.call(
            "account.report.annotation",
            "write",
            [[existingAnnotation.id], { text: editedAnnotation.text, date: editedAnnotation.date }],
            {
                context: this.props.controller.context,
            }
        );
        await this.currentPromise;
        await this.refreshAnnotations();
    }
}
