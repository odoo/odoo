import { Component, useState, useRef, useEffect } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { DateTimeInput } from "@web/core/datetime/datetime_input";

const { DateTime } = luxon;

export class AnnotationPopoverLine extends Component {
    static template = "account_report.AnnotationPopoverLine";
    static props = {
        annotation: {
            type: Object,
            shape: {
                date: { type: [DateTime, { value: false }, { value: null }], optional: true },
                text: String,
                lineID: String,
                id: { type: Number, optional: true },
            },
        },
        onEdit: Function,
        onDelete: Function,
    };
    static components = {
        DateTimeInput,
    };

    setup() {
        this.applyAutoresizeToAll(".annotation_popover_autoresize_textarea");
        this.annotation = useState(this.props.annotation);
        this.notificationService = useService("notification");
        if (this.annotation.text.length) {
            this.textArea = useRef("annotationText");
        } else {
            this.textArea = useAutofocus({ refName: "annotationText" });
        }
    }

    applyAutoresizeToAll(selector) {
        useEffect(() => {
            const resizeTextArea = (textarea) => {
                textarea.style.height = `${textarea.scrollHeight}px`;
                textarea.parentElement.style.height = `${textarea.scrollHeight}px`;
            };

            const textareas = document.querySelectorAll(selector);
            for (const textarea of textareas) {
                Object.assign(textarea.style, {
                    width: "auto",
                    paddingTop: 0,
                    paddingBottom: 0,
                });
                resizeTextArea(textarea);
                textarea.addEventListener("input", () => {
                    resizeTextArea(textarea);
                });
            }
        });
    }

    annotationEditDate(date) {
        this.annotation.date = date;
        this.props.onEdit(this.annotation);
    }

    annotationEditText() {
        if (this.textArea.el.value) {
            if (this.textArea.el.value !== this.annotation.text) {
                this.annotation.text = this.textArea.el.value;
                this.props.onEdit(this.annotation);
            }
        } else {
            this.notificationService.add(_t("The annotation shouldn't have an empty value."));
        }
    }

    deleteAnnotation() {
        this.props.onDelete(this.annotation.id);
    }
}
