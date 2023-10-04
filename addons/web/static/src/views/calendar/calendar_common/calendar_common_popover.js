/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { is24HourFormat } from "@web/core/l10n/dates";
import { Field } from "@web/views/fields/field";
import { getFormattedDateSpan } from "@web/views/calendar/utils";
import { getFieldsSpec } from "@web/model/relational_model/utils";
import { Component } from "@odoo/owl";
import { useModel } from "@web/model/model";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export class CalendarCommonPopover extends Component {
    setup() {
        this.time = null;
        this.timeDuration = null;
        this.date = null;
        this.dateDuration = null;
        const modelParams = {
            config: {
                resModel: this.props.model.resModel,
                resId: this.props.record.id,
                resIds: [this.props.record.id],
                fields: this.props.model.fields,
                activeFields: this.props.model.activeFields,
                isMonoRecord: true,
                mode: "readonly",
            },
            hooks: {},
        };
        const values = this.props.record.rawRecord;

        // This extension is here to load from values (that should be
        // transformed to unity spec)
        class RelationalModelWithValues extends RelationalModel {
            setup() {
                super.setup(...arguments);
                this._dataTransformed = false;
            }

            async load() {
                if (!this._dataTransformed) {
                    this._dataTransformed = true;
                    const proms = [];
                    for (const fieldName in values) {
                        if (
                            ["one2many", "many2many"].includes(this.config.fields[fieldName].type)
                        ) {
                            if (
                                values[fieldName].length &&
                                typeof values[fieldName][0] === "number"
                            ) {
                                const resModel = this.config.fields[fieldName].relation;
                                const resIds = values[fieldName];
                                const activeField = modelParams.config.activeFields[fieldName];
                                if (activeField.related) {
                                    const { activeFields, fields } = activeField.related;
                                    const fieldSpec = getFieldsSpec(activeFields, fields, {});
                                    const kwargs = {
                                        context: activeField.context || {},
                                        specification: fieldSpec,
                                    };
                                    proms.push(
                                        this.orm
                                            .webRead(resModel, resIds, kwargs)
                                            .then((records) => {
                                                values[fieldName] = records;
                                            })
                                    );
                                }
                            }
                        }
                        if (this.config.fields[fieldName].type === "many2one") {
                            const loadDisplayName = async (resId) => {
                                const resModel = this.config.fields[fieldName].relation;
                                const activeField = modelParams.config.activeFields[fieldName];
                                const kwargs = {
                                    context: activeField.context || {},
                                    specification: { display_name: {} },
                                };
                                const records = await this.orm.webRead(resModel, [resId], kwargs);
                                return records[0].display_name;
                            };
                            if (typeof values[fieldName] === "number") {
                                const prom = loadDisplayName(values[fieldName]);
                                prom.then((displayName) => {
                                    values[fieldName] = {
                                        id: values[fieldName],
                                        display_name: displayName,
                                    };
                                });
                                proms.push(prom);
                            } else if (Array.isArray(values[fieldName])) {
                                if (values[fieldName][1] === undefined) {
                                    const prom = loadDisplayName(values[fieldName][0]);
                                    prom.then((displayName) => {
                                        values[fieldName] = {
                                            id: values[fieldName][0],
                                            display_name: displayName,
                                        };
                                    });
                                    proms.push(prom);
                                }
                                values[fieldName] = {
                                    id: values[fieldName][0],
                                    display_name: values[fieldName][1],
                                };
                            }
                        }
                        await Promise.all(proms);
                    }
                }
                this.root = this._createRoot(this.config, values);
            }
        }
        this.model = useModel(RelationalModelWithValues, modelParams);

        this.computeDateTimeAndDuration();
    }

    get activeFields() {
        return this.props.model.activeFields;
    }
    get isEventEditable() {
        return true;
    }
    get isEventDeletable() {
        return this.props.model.canDelete;
    }
    get hasFooter() {
        return this.isEventEditable || this.isEventDeletable;
    }

    isInvisible(fieldNode, record) {
        return evaluateBooleanExpr(fieldNode.invisible, record.evalContextWithVirtualIds);
    }

    computeDateTimeAndDuration() {
        const record = this.props.record;
        const { start, end } = record;
        const isSameDay = start.hasSame(end, "day");

        if (!record.isTimeHidden && !record.isAllDay && isSameDay) {
            const timeFormat = is24HourFormat() ? "HH:mm" : "hh:mm a";
            this.time = `${start.toFormat(timeFormat)} - ${end.toFormat(timeFormat)}`;

            const duration = end.diff(start, ["hours", "minutes"]);
            const formatParts = [];
            if (duration.hours > 0) {
                const hourString = duration.hours === 1 ? _t("hour") : _t("hours");
                formatParts.push(`h '${hourString}'`);
            }
            if (duration.minutes > 0) {
                const minuteStr = duration.minutes === 1 ? _t("minute") : _t("minutes");
                formatParts.push(`m '${minuteStr}'`);
            }
            this.timeDuration = duration.toFormat(formatParts.join(", "));
        }

        if (!this.props.model.isDateHidden) {
            this.date = getFormattedDateSpan(start, end);

            if (record.isAllDay) {
                if (isSameDay) {
                    this.dateDuration = _t("All day");
                } else {
                    const duration = end.plus({ day: 1 }).diff(start, "days");
                    this.dateDuration = duration.toFormat(`d '${_t("days")}'`);
                }
            }
        }
    }

    onEditEvent() {
        this.props.editRecord(this.props.record);
        this.props.close();
    }
    onDeleteEvent() {
        this.props.deleteRecord(this.props.record);
        this.props.close();
    }
}
CalendarCommonPopover.components = {
    Dialog,
    Field,
};
CalendarCommonPopover.template = "web.CalendarCommonPopover";
CalendarCommonPopover.subTemplates = {
    popover: "web.CalendarCommonPopover.popover",
    body: "web.CalendarCommonPopover.body",
    footer: "web.CalendarCommonPopover.footer",
};
CalendarCommonPopover.props = {
    close: Function,
    record: Object,
    model: Object,
    createRecord: Function,
    deleteRecord: Function,
    editRecord: Function,
};
