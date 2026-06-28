import { Record } from "@web/model/record";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Component, props, types as t, signal } from "@odoo/owl";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ViewButton } from "@web/views/view_button/view_button";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";

export class ResourceCalendarAttendancePopover extends Component {
    static template = "resource.ResourceCalendarAttendancePopover";
    static components = {
        Record,
        Dropdown,
        DropdownItem,
        FormRenderer,
        ViewButton,
    };
    static additionalFieldsToFetch = [
        { name: "calendar_id", type: "many2one", readonly: false },
        { name: "display_name", type: "char", readonly: false },
        { name: "date", type: "date", readonly: false },
        { name: "duration_based", type: "boolean", readonly: false },
        { name: "recurrency_excluded_occurences", type: "json", readonly: false },
    ];

    props = props({
        close: t.function(),
        onReload: t.function(),
        recordProps: t.object(),
        archInfo: t.object(),
        context: t.object(),
        resourceCalendarPlugin: t.instanceOf(ResourceCalendarPlugin).optional(),
        originalRecord: t.record().optional(),
        startOcurrenceDateTime: t.instanceOf(luxon.DateTime).optional(),
        endOcurrenceDateTime: t.instanceOf(luxon.DateTime).optional(),
        delta: t.object().optional(),
        startDelta: t.object().optional(),
        endDelta: t.object().optional(),
        isAllDay: t.boolean().optional(),
    });

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.popoverRef = signal(null, { type: t.ref(HTMLElement) });
        this.hasRecurrencyChanged = signal(false, { type: t.boolean() });
        useViewButtons(this.popoverRoot, {
            reload: this.props.onReload,
            afterExecuteAction: this.props.close,
        });
    }

    getDateWithDelta(date) {
        return date.plus(this.props.delta);
    }

    getDate(date) {
        if (this.props.delta) {
            return this.getDateWithDelta(date);
        }
        return date;
    }

    get currentRecordProps() {
        return {
            ...this.props.recordProps,
            resId: this.props.originalRecord?.id,
            mode: "edit",
            context: this.props.context,
            hooks: {
                onRootLoaded: (root) => {
                    root.canSaveOnUpdate = false;
                    if (this.props.delta) {
                        if (this.props.isAllDay) {
                            root.update({
                                duration_based: true,
                            });
                        } else {
                            const start = this.getDateWithDelta(this.props.startOcurrenceDateTime);
                            const end = this.getDateWithDelta(this.props.endOcurrenceDateTime);
                            root.update({
                                hour_from: start.hour + start.minute / 60,
                                hour_to: end.hour + end.minute / 60,
                            });
                        }
                    } else if (this.props.startDelta && this.props.endDelta) {
                        const start = this.props.startOcurrenceDateTime.plus(this.props.startDelta);
                        const end = this.props.endOcurrenceDateTime.plus(this.props.endDelta);
                        root.update({
                            hour_from: start.hour + start.minute / 60,
                            hour_to: end.hour + end.minute / 60,
                        });
                    }
                },
                onRecordChanged: (record, changes) => {
                    this.hasRecurrencyChanged.set(
                        Object.keys(changes).some((field) => field.includes("recurrency"))
                    );
                },
            },
        };
    }

    isFakeRecord(record) {
        return this.props.startOcurrenceDateTime.toISODate() !== record._values.date.toISODate();
    }

    async onSave(record, mode) {
        await executeButtonCallback(this.popoverRef(), async () => {
            if (await record.checkValidity()) {
                try {
                    this.props.resourceCalendarPlugin?.newAttendances.set(true);
                    switch (mode) {
                        case "one": {
                            await record.update({
                                date: this.getDate(this.props.startOcurrenceDateTime),
                            });
                            await this.orm.call(record.resModel, "create_ad_hoc", [
                                [record.resId],
                                serializeDate(this.props.startOcurrenceDateTime),
                                await record.getChanges(),
                            ]);
                            break;
                        }
                        case "following": {
                            await record.update({
                                date: this.getDate(this.props.startOcurrenceDateTime),
                            });
                            await this.orm.call(record.resModel, "create_new_recurrency", [
                                [record.resId],
                                serializeDate(this.props.startOcurrenceDateTime),
                                await record.getChanges(),
                            ]);
                            break;
                        }
                        default:
                            if (this.props.delta) {
                                await record.update({
                                    date: this.getDateWithDelta(this.props.startOcurrenceDateTime),
                                });
                            }
                            await record.save();
                    }
                    this.props.close();
                    await this.props.onReload();
                } catch (error) {
                    return this.notification.add(_t(error.data.message), {
                        type: "danger",
                        className: "o_line_clamp_10",
                    });
                }
            }
        });
    }

    onDiscard(record) {
        if (this.props.delta || this.props.startDelta || this.props.endDelta || !record.resId) {
            this.props.close();
        } else {
            record.discard();
            this.hasRecurrencyChanged.set(false);
        }
    }

    async onDelete(record, mode) {
        await executeButtonCallback(this.popoverRef(), async () => {
            this.props.resourceCalendarPlugin.newAttendances.set(true);
            switch (mode) {
                case "one":
                    await this.orm.call(record.resModel, "exclude_occurence", [
                        [record.resId],
                        serializeDate(this.props.startOcurrenceDateTime),
                    ]);
                    break;
                case "following":
                    await this.orm.call(record.resModel, "stop_recurrency", [
                        [record.resId],
                        serializeDate(this.props.startOcurrenceDateTime),
                    ]);
                    break;
                default:
                    await record.delete();
            }
            this.props.close();
            await this.props.onReload();
        });
    }
}
