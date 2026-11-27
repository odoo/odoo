import { CreatePollOptionDialog } from "@mail/core/common/create_poll_option_dialog";

import { Component, computed, proxy, signal, types, useProps } from "@odoo/owl";

import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { formatDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

/** Duration values are in minutes; "custom" lets the user pick the end time. */
const DURATION_OPTIONS = [
    { value: "10", label: _t("10 minutes") },
    { value: "60", label: _t("1 hour") },
    { value: "240", label: _t("4 hours") },
    { value: "480", label: _t("8 hours") },
    { value: "1440", label: _t("24 hours") },
    { value: "4320", label: _t("3 days") },
    { value: "10080", label: _t("1 week") },
    { value: "20160", label: _t("2 weeks") },
    { value: "custom", label: _t("Custom") },
];

export class CreatePollDialog extends Component {
    static template = "mail.CreatePollDialog";
    static components = { Dialog, Dropdown, DropdownItem, EmojiPicker, CreatePollOptionDialog };

    durationOptions = DURATION_OPTIONS;
    durationRef = signal.ref();
    questionRef = signal.ref();
    durationLabel = computed(() => {
        if (this.state.duration === "custom" && this.state.customEndDt) {
            return formatDateTime(this.state.customEndDt, {
                format: localization.dateTimeFormat.replace(/:ss/, ""),
            });
        }
        return DURATION_OPTIONS.find(({ value }) => value === this.state.duration).label;
    });

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            close: types.function([types.instanceOf(MouseEvent)]),
            thread: types.instanceOf(this.store["mail.thread"]),
        });
        useAutofocus({ ref: this.questionRef, mobile: true });
        this.state = proxy({
            allowMultipleOptions: false,
            customEndDt: null,
            duration: "10",
            /** @type {false | "missing" | "past"} */
            endDtError: false,
            options: [{ label: "" }, { label: "" }],
            question: "",
            submitted: false,
        });
        const state = this.state;
        this.endDtPicker = useDateTimePicker({
            target: this.durationRef,
            // The duration label follows the picked value; clearing it (false)
            // brings the label back to "Custom".
            onChange: (value) => {
                state.customEndDt = value || null;
                state.endDtError = value && this.getEndDtError(value);
            },
            get pickerProps() {
                // Past days are disabled, but a past time of today is accepted so
                // that the user gets an error instead of a silently ignored choice.
                return {
                    minDate: "today",
                    rounding: 1,
                    type: "datetime",
                    value: state.customEndDt,
                };
            },
            showResetButton: true,
            showSeconds: false,
        });
    }

    /**
     * @param {luxon.DateTime|null} endDt
     * @returns {false | "missing" | "past"}
     */
    getEndDtError(endDt) {
        if (!endDt) {
            return "missing";
        }
        return endDt.isValid && endDt > DateTime.now() ? false : "past";
    }

    onClickAddOption() {
        this.state.options.push({ isUserAdded: true, label: "" });
    }

    /**
     * The picker is anchored on the duration toggler: a click on it while the
     * picker is open closes the picker instead of opening the duration menu.
     *
     * @param {MouseEvent} ev
     */
    onClickDuration(ev) {
        if (this.endDtPicker.isOpen()) {
            ev.stopPropagation();
            this.endDtPicker.close();
        }
    }

    onClickRemoveOption(index) {
        this.state.options.splice(index, 1);
    }

    async onClickSubmit() {
        this.state.submitted = true;
        const isCustom = this.state.duration === "custom";
        this.state.endDtError = isCustom && this.getEndDtError(this.state.customEndDt);
        if (this.optionsMissing || this.questionMissing || this.state.endDtError) {
            return;
        }
        await rpc("/mail/poll/create", {
            allow_multiple_options: this.state.allowMultipleOptions,
            options: this.state.options
                .map(({ emoji, label }) => ({ emoji, label: label.trim() }))
                .filter(({ label }) => label),
            duration: isCustom ? undefined : parseInt(this.state.duration),
            end_dt: isCustom ? serializeDateTime(this.state.customEndDt) : undefined,
            question: this.state.question,
            thread_id: this.props.thread.id,
            thread_model: this.props.thread.model,
        });
        this.props.close();
    }

    /** @param {string} value */
    onSelectDuration(value) {
        this.state.duration = value;
        this.state.endDtError = false;
        if (value === "custom") {
            this.endDtPicker.open();
        } else {
            this.endDtPicker.close();
        }
    }

    get optionsMissing() {
        return (
            this.state.submitted &&
            this.state.options.filter(({ label }) => Boolean(label.trim())).length < 2
        );
    }

    get questionMissing() {
        return this.state.submitted && !this.state.question?.trim();
    }
}
