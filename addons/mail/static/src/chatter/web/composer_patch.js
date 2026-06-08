import { props, proxy, t, useEffect } from "@odoo/owl";
import { useLayoutEffect, useRef } from "@web/owl2/utils";

import { patch } from "@web/core/utils/patch";

import { Composer } from "@mail/core/common/composer";
import { RecipientsInput } from "@mail/core/web/recipients_input";

Object.assign(Composer.components, {
    RecipientsInput,
});

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.webComposerProps = props({
            thread: t.instanceOf(this.store["mail.thread"].Class).optional(),
            withMessageFields: t.boolean().optional(),
        });
        this.subjectInputRef = useRef("subjectInput");
        // fill in the "suggested subject" only when it differs from the default
        useLayoutEffect(
            (
                withMessageFields,
                defaultSubject,
                suggestedSubject,
                showSubjectInSmallComposer,
                inputEl
            ) => {
                if (!withMessageFields || !showSubjectInSmallComposer) {
                    return;
                }
                let defaultSubjectStart = defaultSubject;
                if (defaultSubjectStart && defaultSubjectStart.slice(-3) === "...") {
                    defaultSubjectStart = defaultSubjectStart.slice(0, -3);
                }
                if (
                    defaultSubjectStart &&
                    suggestedSubject &&
                    !suggestedSubject.startsWith(defaultSubjectStart) &&
                    inputEl
                ) {
                    inputEl.value = suggestedSubject;
                }
            },
            () => [
                this.webComposerProps.withMessageFields,
                this.webComposerProps.thread?.defaultSubject,
                this.webComposerProps.thread?.suggestedSubject,
                this.webComposerProps.thread?.showSubjectInSmallComposer,
                this.subjectInputRef?.el,
            ]
        );
        this.chatterState = proxy({
            isCcEnabled: false,
        });
        useEffect(
            () => {
                const allRecipients = (
                    this.webComposerProps.thread?.suggestedRecipients || []
                ).concat(this.webComposerProps.thread?.additionalRecipients || []);
                if (allRecipients.some((r) => r.recipient_type === "cc")) {
                    this.chatterState.isCcEnabled = true;
                }
            },
            () => [
                this.webComposerProps.thread?.suggestedRecipients,
                this.webComposerProps.thread?.additionalRecipients,
            ]
        );
    },

    async onClickFullComposerGetAction() {
        const res = await super.onClickFullComposerGetAction();
        if (
            this.webComposerProps.withMessageFields &&
            this.webComposerProps.thread.showSubjectInSmallComposer
        ) {
            res.action.context.default_subject = this.subject;
        }
        return res;
    },

    get postData() {
        const postData = super.postData;
        if (this.subject) {
            postData.subject = this.subject;
        }
        postData.isCcEnabled = this.chatterState.isCcEnabled;
        return postData;
    },

    get subject() {
        return this.subjectInputRef.el?.value;
    },
});
