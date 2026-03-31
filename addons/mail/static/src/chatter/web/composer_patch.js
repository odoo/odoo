import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";

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
                this.props.withMessageFields,
                this.props.thread?.defaultSubject,
                this.props.thread?.suggestedSubject,
                this.props.thread?.showSubjectInSmallComposer,
                this.subjectInputRef?.el,
            ]
        );
        this.chatterState = useState({
            isCcEnabled: false,
        });
        onWillStart(() => this._updateIsCcEnabled(this.props));
        onWillUpdateProps((nextProps) => this._updateIsCcEnabled(nextProps));
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
        postData.isCcEnabled = this.chatterState.isCcEnabled;
        return postData;
    },

    get subject() {
        return this.subjectInputRef.el?.value;
    },

    _updateIsCcEnabled(props) {
        if (props.thread?.additionalCcRecipients?.length) {
            this.chatterState.isCcEnabled = true;
        }
    },

    get isCcEnabled() {
        return this.chatterState.isCcEnabled;
    },

    toggleIsCcEnabled() {
        this.chatterState.isCcEnabled = !this.chatterState.isCcEnabled;
    },
});
