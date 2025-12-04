import { useRef, useEffect } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

import { Composer } from "@mail/core/common/composer";
import { RecipientsInput } from "@mail/core/web/recipients_input";

Composer.props.push("thread?", "withMessageFields?");

Object.assign(Composer.components, {
    RecipientsInput,
});

patch(Composer.prototype, {
    setup() {
        this.subjectInputRef = useRef("subjectInput");
        // fill in the "suggested subject" only when it differs from the default
        useEffect(
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
                if (suggestedSubject !== defaultSubject && inputEl) {
                    inputEl.value = suggestedSubject;
                }
            },
            () => [
                this.props.withMessageFields,
                this.props.thread?.defaultSubject,
                this.props.thread?.suggestedSubject,
                this.props.thread?.showSubjectInSmallComposer,
                this.subjectInputRef?.el,
            ]
        );
        return super.setup();
    },

    async onClickFullComposerGetAction() {
        const res = await super.onClickFullComposerGetAction();
        if (this.props.withMessageFields && this.props.thread.showSubjectInSmallComposer) {
            res.action.context.default_subject = this.subject;
        }
        return res;
    },

    get postData() {
        const postData = super.postData;
        if (this.subject) {
            postData.subject = this.subject;
        }
        return postData;
    },

    get subject() {
        return this.subjectInputRef.el?.value;
    },
});
