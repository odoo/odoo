/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { onWillStart, useState } from "@odoo/owl";

export class AttendanceListController extends ListController {
    static template = "school_management.AttendanceListView";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.attendanceState = useState({
            isStudent: false,
            loaded: false,
            stats: null,
        });

        onWillStart(async () => {
            await this.loadAttendanceStats();
        });
    }

    async loadAttendanceStats() {
        try {
            const isStudent = await user.hasGroup("school_management.group_school_student");
            const isStaff =
                (await user.hasGroup("school_management.group_school_teacher")) ||
                (await user.hasGroup("school_management.group_school_admin")) ||
                (await user.hasGroup("base.group_system"));

            const isStudentRole = isStudent && !isStaff;
            if (isStudentRole) {
                this.attendanceState.isStudent = true;
                const students = await this.orm.searchRead(
                    "university.student",
                    [["user_id", "=", user.userId]],
                    ["id", "name", "attendance_rate"],
                    { limit: 1 }
                );
                if (students && students.length) {
                    const studentId = students[0].id;
                    const attendances = await this.orm.searchRead(
                        "university.attendance",
                        [["student_id", "=", studentId]],
                        ["id", "status"],
                        { limit: 1000 }
                    );
                    let present = 0, absent = 0, late = 0, excused = 0;
                    for (const a of attendances) {
                        if (a.status === "present") present++;
                        else if (a.status === "absent") absent++;
                        else if (a.status === "late") late++;
                        else if (a.status === "excused") excused++;
                    }
                    const total = attendances.length;
                    const rate = total > 0 ? Math.round((present / total) * 100) : (students[0].attendance_rate || 100);
                    this.attendanceState.stats = {
                        rate,
                        present,
                        absent,
                        late,
                        excused,
                        total,
                        isLow: rate < 80,
                    };
                }
            }
        } catch (e) {
            console.error("[AttendanceListController] Error loading stats:", e);
        } finally {
            this.attendanceState.loaded = true;
        }
    }

    _getAttendanceContext() {
        const context = {};
        const domain = this.props.domain || [];
        for (const item of domain) {
            if (Array.isArray(item) && item.length === 3) {
                if (item[0] === "section_id" && item[1] === "=") {
                    context.default_section_id = item[2];
                    context.section_id = item[2];
                }
                if (item[0] === "date" && item[1] === "=") {
                    context.default_date = item[2];
                    context.date = item[2];
                }
            }
        }
        if (this.props.context?.default_section_id) {
            context.default_section_id = this.props.context.default_section_id;
            context.section_id = this.props.context.default_section_id;
        }
        if (this.props.context?.default_date) {
            context.default_date = this.props.context.default_date;
            context.date = this.props.context.default_date;
        }
        return context;
    }

    async createRecord() {
        return this.actionService.doAction("school_management.action_university_attendance_session", {
            additionalContext: this._getAttendanceContext(),
        });
    }
}

export const attendanceListView = {
    ...listView,
    Controller: AttendanceListController,
};

registry.category("views").add("university_attendance_list", attendanceListView);

export class AttendanceKanbanController extends KanbanController {
    static template = "school_management.AttendanceKanbanView";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.attendanceState = useState({
            isStudent: false,
            loaded: false,
            stats: null,
        });

        onWillStart(async () => {
            await this.loadAttendanceStats();
        });
    }

    async loadAttendanceStats() {
        try {
            const isStudent = await user.hasGroup("school_management.group_school_student");
            const isStaff =
                (await user.hasGroup("school_management.group_school_teacher")) ||
                (await user.hasGroup("school_management.group_school_admin")) ||
                (await user.hasGroup("base.group_system"));

            const isStudentRole = isStudent && !isStaff;
            if (isStudentRole) {
                this.attendanceState.isStudent = true;
                const students = await this.orm.searchRead(
                    "university.student",
                    [["user_id", "=", user.userId]],
                    ["id", "name", "attendance_rate"],
                    { limit: 1 }
                );
                if (students && students.length) {
                    const studentId = students[0].id;
                    const attendances = await this.orm.searchRead(
                        "university.attendance",
                        [["student_id", "=", studentId]],
                        ["id", "status"],
                        { limit: 1000 }
                    );
                    let present = 0, absent = 0, late = 0, excused = 0;
                    for (const a of attendances) {
                        if (a.status === "present") present++;
                        else if (a.status === "absent") absent++;
                        else if (a.status === "late") late++;
                        else if (a.status === "excused") excused++;
                    }
                    const total = attendances.length;
                    const rate = total > 0 ? Math.round((present / total) * 100) : (students[0].attendance_rate || 100);
                    this.attendanceState.stats = {
                        rate,
                        present,
                        absent,
                        late,
                        excused,
                        total,
                        isLow: rate < 80,
                    };
                }
            }
        } catch (e) {
            console.error("[AttendanceKanbanController] Error loading stats:", e);
        } finally {
            this.attendanceState.loaded = true;
        }
    }
}

export const attendanceKanbanView = {
    ...kanbanView,
    Controller: AttendanceKanbanController,
};

registry.category("views").add("university_attendance_kanban", attendanceKanbanView);

export class AttendanceFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async create() {
        const dirty = await this.model.root.isDirty();
        const onError = (error, options) => this.onSaveError(error, options, true);
        const canProceed = !dirty || (await this.model.root.save({ onError }));
        if (canProceed) {
            return this.actionService.doAction("school_management.action_university_attendance_session");
        }
    }
}

export const attendanceFormView = {
    ...formView,
    Controller: AttendanceFormController,
};

registry.category("views").add("university_attendance_form", attendanceFormView);
