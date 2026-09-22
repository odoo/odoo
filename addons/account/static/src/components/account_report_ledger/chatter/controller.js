/** @odoo-module native */
import { useState } from "@odoo/owl";
import { AccountReportController } from "@report_formula/components/account_report/controller";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

patch(AccountReportController.prototype, {
    setup() {
        super.setup();
        this.chatterState = useState({
            model: undefined,
            id: undefined,
            lineId: undefined, // To identify the line when editing / deleting a message
        });
    },

    onLoaded() {
        super.onLoaded();
        if (!this.ui.isSmall) {
            const chatterState = JSON.parse(
                browser.sessionStorage.getItem(this.sessionChatterStateID()),
            );
            this.chatterState.model = chatterState?.model;
            this.chatterState.id = chatterState?.id;
            this.chatterState.lineId = chatterState?.lineId;
        }
    },

    onReportDisplayed() {
        super.onReportDisplayed();
        this.refreshVisibleAnnotations();
    },

    onLinesUnfolded(lineStartIndex, lineEndIndex) {
        super.onLinesUnfolded(lineStartIndex, lineEndIndex);
        this.loadAnnotations(lineStartIndex, lineEndIndex);
    },

    get annotations() {
        return this.data.annotations;
    },

    set annotations(value) {
        this.data.annotations = value;
    },

    sessionChatterStateID() {
        return this.sessionOptionsID() + user.activeCompany.id.toString() + ".chatter";
    },

    async loadAnnotations(lineStartIndex = 0, lineEndIndex = this.lines.length) {
        const new_annotations = await this.orm.call(
            "report.formula",
            "get_annotations",
            [
                this.action.context.report_id,
                this.options,
                this.lines.slice(lineStartIndex, lineEndIndex),
            ],
        );
        for (const [key, value] of Object.entries(new_annotations)) {
            this.annotations[key] = value;
        }

        this.refreshVisibleAnnotations(lineStartIndex, lineEndIndex);
    },

    addAnnotation(messageId, resModel, resId, body) {
        this.lines.forEach((line) => {
            if (line.chatter?.model === resModel && line.chatter?.id === resId) {
                this.annotations[line.id] = this.annotations[line.id] || [];
                this.annotations[line.id].push({
                    id: messageId,
                    model: resModel,
                    res_id: resId,
                    body: body,
                });
                line.visible_annotations = true;
            }
        });
    },

    removeAnnotation(messageId) {
        this.lines.forEach((line) => {
            this.annotations[line.id] = (this.annotations[line.id] || []).filter(
                (annotation) => annotation.id !== messageId,
            );
        });
        this.refreshVisibleAnnotations();
    },

    async toggleLineChatter(annotation) {
        if (
            this.chatterState.model === annotation.resModel &&
            this.chatterState.id === annotation.resId &&
            this.chatterState.lineId === annotation.line_id
        ) {
            this.closeChatter();
        } else {
            this.chatterState.model = annotation.resModel;
            this.chatterState.id = annotation.resId;
            this.chatterState.lineId = annotation.line_id;
            browser.sessionStorage.setItem(
                this.sessionChatterStateID(),
                JSON.stringify({
                    model: this.chatterState.model,
                    id: this.chatterState.id,
                    lineId: this.chatterState.lineId,
                }),
            );
        }
    },

    closeChatter() {
        this.chatterState.model = undefined;
        this.chatterState.id = undefined;
        this.chatterState.lineId = undefined;
        browser.sessionStorage.removeItem(this.sessionChatterStateID());
    },

    refreshVisibleAnnotations(lineStartIndex = 0, lineEndIndex = this.lines.length) {
        this.lines.slice(lineStartIndex, lineEndIndex).forEach((line) => {
            line.visible_annotations =
                this.annotations[line.id] && this.annotations[line.id].length > 0;
        });
    },
});
