/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { DynamicGroupList } from "@web/model/relational_model/dynamic_group_list";
import { getPropertyFieldInfo } from "@web/views/fields/field";
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
import { TimesheetTimerListController } from "@timesheet_grid/views/timesheet_list/timesheet_timer_list_controller";
import { TimesheetTimerKanbanController } from "@timesheet_grid/views/timesheet_kanban/timesheet_timer_kanban_controller";

export class TimesheetTimerRendererHook {
    constructor(propsList, env) {
        this.propsList = propsList;
        this.env = env;
        this.setup();
    }

    setup() {
        this.orm = useService("orm");
        this.timesheetUOMService = useService("timesheet_uom");
        this.notification = useService("notification");
        this.timerState = useState({
            timesheetId: undefined,
            addTimeMode: false,
            timerRunning: false,
            otherCompany: false,
        });
    }

    get showTimer() {
        return this.timesheetUOMService.timesheetWidget === "float_time";
    }

    getFieldInfo(fieldName, field) {
        const fieldInfo = getPropertyFieldInfo({
            field: field,
            name: fieldName,
            type: field.type,
            domain: field.domain || "[]",
            required: "False",
        });
        fieldInfo.placeholder = field.string || "";
        if (fieldName === "project_id") {
            fieldInfo.domain = Domain.and([
                fieldInfo.domain,
                new Domain([["allow_timesheets", "=", true]]),
            ]).toString();
            fieldInfo.context = `{'search_default_my_projects': True}`;
            fieldInfo.required = "True";
        } else if (fieldName === "task_id") {
            fieldInfo.context = `{'default_project_id': project_id, 'search_default_my_tasks': True, 'search_default_open_tasks': True}`;
        } else if (fieldName === "name") {
            fieldInfo.placeholder = _t("Describe your activity...");
        }
        if (field.depends?.length) {
            fieldInfo.onChange = true;
        }
        return fieldInfo;
    }

    get fields() {
        const fields = {};
        for (const [fieldName] of Object.entries(this.propsList.activeFields)) {
            const fieldInfo = this.getFieldInfo(fieldName, this.propsList.fields[fieldName]);
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
        if (this.timesheet && this.env.config.viewType === 'kanban') {
            await this.propsList.enterEditMode(this.timesheet);
        }
        this._setAddTimeMode(this.timerState.addTimeMode);
    }

    async _newTimesheetTimer() {
        if (this.propsList.addNewRecord) {
            return this.propsList.addNewRecord(true);
        }
        const values = await this.propsList.model._loadNewRecord({
            resModel: this.propsList.resModel,
            activeFields: this.propsList.activeFields,
            fields: this.propsList.fields,
            context: this.propsList.context,
        });
        if (values.project_id) {
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
        let timesheetData = await this.orm.call(
            this.propsList.resModel,
            "action_start_new_timesheet_timer",
            [{}]
        );
        if (timesheetData === false) {
            this.timesheet = await this._newTimesheetTimer();
            timesheetData = {
                ...this.timesheet.data,
                id: false,
            };
        }
        this._setTimerStateData(timesheetData);
        await this.propsList.model.load();
    }

    async _onTimerStopped() {
        const timesheetId = this.timesheet.resId;
        const tryToMatch = this.timesheet && !this.timesheet.data.unit_amount;
        this.timesheet = undefined;
        this._resetTimerState();

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
        const timesheetId = this.timesheet?.id;
        if (timesheetId) {
            this.propsList._removeRecords([timesheetId]);
        }
        this.timesheet = undefined;
        this._resetTimerState();
        this.propsList.model.load();
    }

    async _popRecord(propsList = this.propsList) {
        if (
            !this.timerState.timesheetId ||
            (this.timesheet &&
                this.timesheet.resId === this.timerState.timesheetId) ||
            this.timerState.otherCompany
        ) {
            if (this.timesheet?.data.project_id) {
                this.timesheet = undefined;
            }
            return;
        }

        let timesheet = propsList.records.find((record) => record.resId === this.timerState.timesheetId);
        if (!timesheet && propsList instanceof DynamicRecordList) {
            timesheet = await propsList.addExistingRecord(this.timerState.timesheetId, true);
        }
        /*
            If the timesheet was not found in the propsList, and the view is grouped, this means that the timesheet
            should be placed in one of the folded section. But since the records of the folded section are not loaded,
            we don't have access to a DynamicRecordList directly.
        */
        if (!timesheet && propsList instanceof DynamicGroupList) {
            const foldedList = this._getFoldedList(propsList);
            let recordList = await this._getDynamicRecordList(foldedList);
            /*
                We do not need to target the correct folded section, any one is fine.
                When a section is unfolded, the records are loaded, so it make sense that the record appears inside the
                correct section. Before the section is unfolded though, it's still unclear why the record is computed in
                the correct section total despite it being added in a random recordList from the view.
            */
            timesheet = await recordList.addExistingRecord(this.timerState.timesheetId, true);
        }
        if (!timesheet) {
            return;
        }
        this.timesheet = timesheet;
    }

    /*
        list : the props list that was passed to the popRecord method.
        return : the first dynamicGroupList that is folded.
    */
    _getFoldedList(list) {
        for (const groupId in list.groups) {
            if (list.groups[groupId]._config.isFolded) {
                return list.groups[groupId].list;
            }
            // the current group is unfolded, but it contains other dynamicGroupList, we have to check them too.
            if (list.groups[groupId].list instanceof DynamicGroupList) {
                const foldedList =  this._getFoldedList(list.groups[groupId].list);
                if (foldedList) {
                    return foldedList;
                }
            }
        }
        // all the subgroups of the list are unfolded, we can not use this list as default.
        return false;
    }

    async _getDynamicRecordList(list) {
        while (list instanceof DynamicGroupList) {
            // This means that the current DynamicGroupList contains a DynamicRecordList
            if (list.groups[0] !== undefined) {
                return list.group[0].list;
            }
            await list.load();
            list = list.groups[0].list;
        }
        return list;
    }

    async _fetchRunningTimer() {
        const result = await this.orm.call(this.propsList.resModel, "get_running_timer", []);
        this._setTimerStateData(result);
    }

    _setTimerStateData(vals) {
        if (vals.id || vals.other_company) {
            Object.assign(this.timerState, {
                timerRunning: true,
                timesheetId: vals.id,
                otherCompany: !!vals.other_company,
            });
        } else if (this.timerState.timerRunning && this.timesheet?.data.project_id) {
            this._resetTimerState();
        }
        if ("step_timer" in vals) {
            this.timerState.stepTimer = vals.step_timer;
        }
    }

    _setAddTimeMode(addTimeMode) {
        this.timerState.addTimeMode = addTimeMode;
    }

    _resetTimerState() {
        Object.assign(this.timerState, {
            timesheetId: undefined,
            timerRunning: false,
            otherCompany: false,
        });
    }

    _onKeydown(ev) {
        if (
            this.propsList.editedRecord ||
            ev.target.closest(".modal") ||
            ['input', 'textarea'].includes(ev.target.tagName.toLowerCase())
        ) {
            return;
        }
        const { otherCompany, timerRunning } = this.timerState;
        switch (ev.key) {
            case "Enter":
                ev.preventDefault();
                if (!otherCompany) {
                    if (timerRunning) {
                        this._onTimerStopped();
                    } else {
                        this._onTimerStarted();
                    }
                }
                break;
            case "Escape":
                if (!otherCompany && timerRunning) {
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

const patchController = () => ({
    onChangeWriteValues(record) {
        const { project_id, task_id, name } = record._getChanges();
        return {
            project_id,
            task_id,
            name,
        };
    },

    get modelParams() {
        const params = super.modelParams;
        params.hooks.onRecordChanged = async (record) => {
            if (record.isNew) {
                if (!record.data.project_id || !record.data.is_timer_running) {
                    return params;
                }
                const { project_id, task_id, employee_id, user_id, company_id } = record.data;
                await record.model.orm.call(record.resModel, "action_start_new_timesheet_timer", [
                    {
                        project_id: project_id && project_id[0],
                        task_id: task_id && task_id[0],
                        employee_id: employee_id && employee_id[0],
                        user_id: user_id && user_id[0],
                        company_id: company_id && company_id[0],
                    },
                ]);
            } else if (record.data.is_timer_running) {
                const writeValues = this.onChangeWriteValues(record);
                if (writeValues.project_id != false) {
                    await record.model.orm.write(
                        record.resModel,
                        [record.resId],
                        writeValues
                    );
                }
            }
        };
        return params;
    },
});

patch(TimesheetTimerListController.prototype, patchController());
patch(TimesheetTimerKanbanController.prototype, patchController());
