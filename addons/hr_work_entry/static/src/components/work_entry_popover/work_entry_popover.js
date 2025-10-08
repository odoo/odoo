import { formatFloatTime } from "@web/views/fields/formatters";
import { Record } from "@web/model/record";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Component, useRef, useState } from "@odoo/owl";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { serializeDate } from "@web/core/l10n/dates";

export class WorkEntryPopover extends Component {
    static template = "hr_work_entry.WorkEntryPopover";
    static components = {
        Record,
        FormRenderer,
        ViewButton,
    };
    static props = {
        close: Function,
        readonly: { type: Boolean },
        onReload: Function,
        originalRecord: { type: Object },
        recordProps: { type: Object },
        archInfo: { type: Object },
        getSource: Function,
        getDurationStr: Function,
    };

    setup() {
        this.state = useState({
            isSplit: false,
            originalDuration: this.props.originalRecord.duration,
            newRecordValues: {
                work_entry_type_id: false,
                color: false,
                display_code: false,
                duration: 0,
                name: "",
            },
        });
        this.rootRef = useRef("root");
        useViewButtons(this.rootRef, {
            reload: this.props.onReload,
            afterExecuteAction: this.props.close,
        });
    }

    getSource(record) {
        if (this.source) {
            return this.source;
        }
        return (this.source = this.props.getSource(record));
    }

    onOpenSource(record) {
        this.getSource(record)?.onOpen();
    }

    get currentRecordProps() {
        return {
            ...this.props.recordProps,
            resId: this.props.originalRecord.id,
            mode: this.props.readonly ? "readonly" : "edit",
            hooks: {
                onRecordChanged: (record, changes) => {
                    if (changes.duration) {
                        this.state.newRecordValues = {
                            ...this.state.newRecordValues,
                            duration: Math.max(
                                0,
                                this.state.originalDuration - record.data.duration
                            ),
                        };
                    }
                    if (!changes.name && !record.data.is_manual) {
                        record.update({ is_manual: true }, { save: false });
                    }
                },
            },
        };
    }

    newRecordProps(currentRecord) {
        return {
            ...this.props.recordProps,
            mode: "edit",
            values: {
                ...currentRecord.data,
                ...this.state.newRecordValues,
                is_manual: true,
                date: serializeDate(currentRecord.data.date),
            },
            hooks: {
                onRecordChanged: (record, changes) => {
                    this.state.newRecordValues = record.data;
                },
            },
        };
    }

    get archInfo() {
        return this.props.archInfo;
    }

    getDurationStr(duration) {
        const durationStr = formatFloatTime(duration, {
            noLeadingZeroHour: true,
        }).replace(/(:00|:)/g, "h");
        return ` ${durationStr}`;
    }

    onToggleSplit() {
        this.state.isSplit = !this.state.isSplit;
    }

    async onSave(currentRecord, newRecord) {
        await executeButtonCallback(this.rootRef.el, async () => {
            const areValid =
                (await currentRecord.checkValidity()) &&
                (!this.state.isSplit || (await newRecord.checkValidity()));
            if (areValid) {
                if (this.state.isSplit) {
                    await newRecord.save();
                }
                await currentRecord.save();
                await this.props.onReload();
                this.props.close();
            }
        });
    }
}
