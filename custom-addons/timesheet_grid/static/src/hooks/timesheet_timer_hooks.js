/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import {
    useState,
    useComponent,
    onWillStart,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useEffect,
    useExternalListener,
    useSubEnv,
} from "@odoo/owl";

export class TimesheetTimerRendererHook {
    constructor(propsList, env) {
        this.propsList = propsList;
        this.env = env;
        this.setup();
        this._setProjectTaskDebounce = useDebounced(this._setProjectTask.bind(this), 500);
    }

    setup() {
        this.orm = useService("orm");
        this.timesheetUOMService = useService("timesheet_uom");
        this.timerState = useState({
            timesheetId: undefined,
            taskId: undefined,
            projectId: undefined,
            addTimeMode: false,
            startSeconds: 0,
            timerRunning: false,
            headerReadonly: false,
        });
        this.propsList.model.hooks.onRecordChanged = this.onRecordChanged.bind(this);
    }

    get showTimer() {
        return this.timesheetUOMService.timesheetWidget === "float_time" && this.propsList.context?.my_timesheet_display_timer;
    }

    get fields() {
        const fields = {};
        for (const [fieldName, field] of Object.entries(this.propsList.activeFields)) {
            const fieldInfo = { ...field };
            if (fieldName === "project_id") {
                if (field.domain) {
                    fieldInfo.domain = Domain.and([
                        field.domain,
                        [["timesheet_encode_uom_id", "=", this.timesheetUOMService.timesheetUOMId]],
                    ]).toList();
                } else {
                    fieldInfo.domain = [
                        ["allow_timesheets", "=", true],
                        ["timesheet_encode_uom_id", "=", this.timesheetUOMService.timesheetUOMId],
                    ];
                }
                fieldInfo.required = "True";
                if (!fieldInfo.placeholder && fieldInfo.string) {
                    fieldInfo.placeholder = fieldInfo.string;
                }
                fieldInfo.context = `{'search_default_my_projects': True}`;
            } else if (fieldName === "task_id") {
                if (!fieldInfo.placeholder && fieldInfo.string) {
                    fieldInfo.placeholder = fieldInfo.string;
                }
                fieldInfo.context = `{'default_project_id': project_id, 'search_default_my_tasks': True, 'search_default_open_tasks': True}`;
            } else if (fieldName === "name") {
                if (fieldInfo.required) {
                    fieldInfo.required = "False";
                }
                fieldInfo.placeholder = _t("Describe your activity...");
            }
            if (field.depends?.length && !fieldInfo.onChange) {
                fieldInfo.onChange = true;
            }
            fields[fieldName] = fieldInfo;
        }
        return fields;
    }

    async onWillStart() {
        await this._fetchRunningTimer();
        await this._popRecord();
        this._setAddTimeMode(false);
    }

    async onMounted() {
        if (this.timesheet) {
            await this.propsList.enterEditMode(this.timesheet);
        }
    }

    onWillUnmount() {}

    async onWillUpdateProps(nextProps) {
        await this._fetchRunningTimer();
        await this._popRecord(nextProps.list);
        this._setAddTimeMode(this.timerState.addTimeMode);
    }

    onRecordChanged(record, changes) {
        if (this.timerState.timesheetId === record.resId) {
            if (changes.project_id) {
                this.timerState.projectId = changes.project_id;
            }
            if (changes.task_id) {
                this.timerState.taskId = changes.task_id;
            }
            this.timesheet.save({ reload: false }).then(() => {
                if (!this.timerState.timesheetId) {
                    const { resId } = this.timesheet;
                    this.timerState.timesheetId = resId;
                    this.orm.call(this.propsList.resModel, "action_timer_start", [resId]);
                }
            });
        }
    }

    async newTimesheetTimer() {
        const values = await this.propsList.model._loadNewRecord({
            resModel: this.propsList.resModel,
            activeFields: this.propsList.activeFields,
            fields: this.propsList.fields,
            context: this.propsList.context,
        });
        if (values.project_id) {
            this.timerState.projectId = values.project_id.id;
            const timesheetTimerData = await this.startNewTimesheetTimer(values);
            if (timesheetTimerData.id) {
                values.id = timesheetTimerData.id;
            }
        }
        return new this.propsList.model.constructor.Record(
            this.propsList.model,
            {
                context: this.propsList.context,
                activeFields: this.propsList.activeFields,
                resModel: this.propsList.resModel,
                fields: this.propsList.fields,
                resId: values.id || false,
                resIds: values.id ? [values.id] : [],
                isMonoRecord: true,
                currentCompanyId: this.propsList.currentCompanyId,
                mode: "edit",
            },
            values,
            { manuallyAdded: !values.id }
        );
    }

    async _onTimerStarted() {
        this.timerState.timerRunning = true;
        this.timerState.addTimeMode = false;
        this.timerState.startSeconds = Math.floor(Date.now() / 1000);
        this.timesheet = await this.newTimesheetTimer();
        this.timerState.timesheetId = this.timesheet.resId;
    }

    async _onTimerStopped() {
        const timesheetId = this.timesheet.resId;
        const tryToMatch = this.timesheet && !this.timesheet.data.unit_amount;
        this.timesheet = undefined;
        this.timerState.timesheetId = undefined;
        this.timerState.projectId = undefined;
        this.timerState.taskId = undefined;
        this.timerState.timerRunning = false;
        this.timerState.headerReadonly = false;

        await this.orm.call(this.propsList.resModel, "action_timer_stop", [
            timesheetId,
            tryToMatch,
        ]);
        this.propsList.model.load();
    }

    async _onTimerUnlinked() {
        if (this.timerState.timesheetId !== false) {
            await this.orm.call(this.propsList.resModel, "action_timer_unlink", [
                this.timerState.timesheetId,
            ]);
        }
        this.timesheet = undefined;
        this.timerState.timesheetId = undefined;
        this.timerState.projectId = undefined;
        this.timerState.taskId = undefined;
        this.timerState.timerRunning = false;
        this.timerState.headerReadonly = false;
        this.propsList.model.load();
    }

    async _popRecord(propsList = this.propsList) {
        if (
            !this.timerState.timesheetId ||
            (this.timesheet &&
                this.timesheet.resId === this.timerState.timesheetId) ||
            this.timerState.headerReadonly
        ) {
            return;
        }

        let timesheet = propsList.records.find((record) => record.resId === this.timerState.timesheetId);
        if (!timesheet && propsList instanceof DynamicRecordList) {
            timesheet = await propsList.addExistingRecord(this.timerState.timesheetId, true);
        }
        if (!timesheet) {
            return;
        }
        this.timesheet = timesheet;
    }

    async _fetchRunningTimer() {
        const result = await this.orm.call(this.propsList.resModel, "get_running_timer", []);
        this._setTimerStateData(result);
    }

    _setTimerStateData(vals) {
        if (vals.id !== undefined) {
            this.timerState.timerRunning = true;
            this.timerState.timesheetId = vals.id;
            this.timerState.headerReadonly = vals.readonly;
            this.timerState.projectId = vals.project_id;
            this.timerState.taskId = vals.task_id || undefined;
            this.timerState.timerRunning = true;
            this.timerState.startSeconds = Math.floor(Date.now() / 1000) - vals.start;
        } else if (this.timerState.timerRunning && this.timerState.projectId) {
            this.timerState.headerReadonly = false;
            this.timerState.timesheetId = undefined;
            this.timerState.projectId = undefined;
            this.timerState.taskId = undefined;
            this.timerState.timerRunning = false;
        }
        if ("step_timer" in vals) {
            this.timerState.stepTimer = vals.step_timer;
        }
    }

    async startNewTimesheetTimer(vals = {}) {
        const getValue = (fieldName, value) =>
            this.propsList.fields[fieldName].type === "many2one" ? value[0] : value;
        const values = {};
        for (const [key, value] of Object.entries(vals)) {
            values[key] = getValue(key, value);
        }
        return await this.orm.call(this.propsList.resModel, "action_start_new_timesheet_timer", [
            values,
        ]);
    }

    async _setProjectTask() {
    }

    _setAddTimeMode(addTimeMode) {
        this.timerState.addTimeMode = addTimeMode;
    }

    _onKeydown(ev) {
        if (
            this.propsList.editedRecord ||
            ['input', 'textarea'].includes(ev.target.tagName.toLowerCase())
        ) {
            return;
        }
        switch (ev.key) {
            case "Enter":
                ev.preventDefault();
                if (this.timerState.timerRunning) {
                    this._onTimerStopped();
                } else {
                    this._onTimerStarted();
                }
                break;
            case "Escape":
                if (this.timerState.timerRunning) {
                    ev.preventDefault();
                    this._onTimerUnlinked();
                }
                break;
            case "Shift":
                ev.preventDefault();
                this._setAddTimeMode(true);
                break;
        }
    }

    _onKeyup(ev) {
        if (ev.key === "Shift") {
            this._setAddTimeMode(false);
        }
    }

    async onTimerHeaderClick(ev) {
        if (this.timesheet && !this.timesheet.isInEdition) {
            this.propsList.leaveEditMode();
            await this.propsList.enterEditMode(this.timesheet);
        }
    }
}

export function useTimesheetTimerRendererHook() {
    const component = useComponent();
    const timesheetTimerRendererHook = new TimesheetTimerRendererHook(component.props.list, component.env);
    useSubEnv({
        timerState: timesheetTimerRendererHook.timerState,
    });
    onWillStart(timesheetTimerRendererHook.onWillStart.bind(timesheetTimerRendererHook));
    onMounted(timesheetTimerRendererHook.onMounted.bind(timesheetTimerRendererHook));
    onWillUnmount(timesheetTimerRendererHook.onWillUnmount.bind(timesheetTimerRendererHook));
    onWillUpdateProps(
        timesheetTimerRendererHook.onWillUpdateProps.bind(timesheetTimerRendererHook)
    );
    useEffect(
        (reloadTimer) => {
            if (reloadTimer) {
                timesheetTimerRendererHook._fetchRunningTimer();
            }
        },
        () => [component.props.timerState?.reload]
    );
    useExternalListener(
        window,
        "keydown",
        timesheetTimerRendererHook._onKeydown.bind(timesheetTimerRendererHook)
    );
    useExternalListener(
        window,
        "keyup",
        timesheetTimerRendererHook._onKeyup.bind(timesheetTimerRendererHook)
    );
    return timesheetTimerRendererHook;
}
