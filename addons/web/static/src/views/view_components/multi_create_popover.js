// @ts-check

/** @module @web/views/view_components/multi_create_popover - Popover with mini form and optional time range picker for quick-creating records */

import { Component } from "@odoo/owl";
import { TimePicker } from "@web/components/time_picker/time_picker";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import { useCallbackRecorder } from "@web/search/action_hook";
import { FormRenderer } from "@web/views/form/form_renderer";

/** Popover with a mini form and optional time range picker for quick-creating records in calendar/gantt views. */
export class MultiCreatePopover extends Component {
    static template = "web.MultiCreatePopover";
    static components = {
        FormRenderer,
        Record,
        TimePicker,
    };
    static props = {
        close: Function,
        multiCreateArchInfo: Object,
        multiCreateRecordProps: Object,
        onAdd: Function,
        callbackRecorder: Object,
        timeRange: { type: [Object, { value: null }] },
    };

    setup() {
        this.notification = useService("notification");

        this.multiCreateData = {
            timeRange: this.props.timeRange && { ...this.props.timeRange },
        };
        this.multiCreateArchInfo = this.props.multiCreateArchInfo;
        this.multiCreateRecordProps = {
            ...this.props.multiCreateRecordProps,
            hooks: {
                onRootLoaded: (record) => {
                    this.multiCreateData.record = record;
                },
                onDisplayInvalidFields: () =>
                    this.notification.add(_t("Missing required fields"), {
                        type: "danger",
                    }),
            },
        };

        useCallbackRecorder(this.props.callbackRecorder, () => this.multiCreateData);
    }

    /** @param {{ start: Time, end: Time }} timeRange */
    setMultiCreateTimeRange(timeRange) {
        Object.assign(this.multiCreateData.timeRange, timeRange);
    }

    /**
     * Validate the form record and time range, showing notifications on failure.
     * @returns {Promise<boolean>}
     */
    async isValidMultiCreateData() {
        const isValid = await this.multiCreateData.record.checkValidity({
            displayNotification: true,
        });
        if (!isValid) {
            return false;
        }
        if (this.multiCreateData.timeRange) {
            const { start, end } = this.multiCreateData.timeRange;
            if (!start || !end) {
                this.notification.add(_t("Invalid time range"), {
                    title: "User Error",
                    type: "warning",
                });
                return false;
            }
            if (
                luxon.DateTime.fromObject(start.toObject()) >
                luxon.DateTime.fromObject(end.toObject())
            ) {
                this.notification.add(_t("Start time should be before end time"), {
                    title: "User Error",
                    type: "warning",
                });
                return false;
            }
        }
        return true;
    }

    /** Validate and propagate the creation data to the parent, then close the popover. */
    async onAdd() {
        const isValid = await this.isValidMultiCreateData();
        if (isValid) {
            this.props.onAdd(this.multiCreateData);
            this.props.close();
        }
    }
}
