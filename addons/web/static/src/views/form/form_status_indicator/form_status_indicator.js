import { Component, onWillUnmount, proxy, status, t, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useBus } from "@web/core/utils/hooks";

/** Kept in step with the fade timed by `form_status_indicator.scss`. */
const FEEDBACK_DURATION = 2000;

export function useStatusIndicator(model, actions = {}) {
    const _fieldIsDirty = proxy({ value: false });
    useBus(model.bus, "FIELD_IS_DIRTY", (ev) => {
        _fieldIsDirty.value = ev.detail;
    });

    return {
        props() {
            const { root } = model;
            return {
                isDirty: root.dirty || _fieldIsDirty.value,
                isValid: root.isValid,
                isNew: root.isNew && !root.offlineId,
                save: actions.save,
                discard: actions.discard,
            };
        },
    };
}

export class FormStatusIndicator extends Component {
    static template = "web.FormStatusIndicator";
    props = useProps({
        isDirty: t.boolean(),
        isValid: t.boolean().optional(true),
        isNew: t.boolean().optional(false),
        save: t.function(),
        discard: t.function(),
    });

    setup() {
        this.state = proxy({ feedback: undefined });
        onWillUnmount(() => browser.clearTimeout(this.feedbackTimeout));
    }

    showFeedback(text, icon, className) {
        // Discarding a new record navigates back, which destroys this one.
        if (status(this) !== "mounted") {
            return;
        }
        browser.clearTimeout(this.feedbackTimeout);
        this.state.feedback = { text, icon, className };
        this.feedbackTimeout = browser.setTimeout(
            () => (this.state.feedback = undefined),
            FEEDBACK_DURATION
        );
    }

    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get indicatorMode() {
        const { isValid, isNew, isDirty } = this.props;
        if (isNew || isDirty) {
            return isValid ? "dirty" : "invalid";
        }
        return "saved";
    }

    async discard() {
        await this.props.discard();
        this.showFeedback(_t("Discarded"), "close", "text-muted");
    }
    async save() {
        // Only once it really went through: a failed or aborted save must not
        // claim otherwise. Discarding has no such outcome to check.
        if (!(await this.props.save())) {
            return;
        }
        this.showFeedback(_t("Saved"), "check", "text-success");
    }
}
