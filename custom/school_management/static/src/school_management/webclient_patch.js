/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { KanbanRecord, getImageSrcFromRecordInfo } from "@web/views/kanban/kanban_record";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { user } from "@web/core/user";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";
import { useService, useBus } from "@web/core/utils/hooks";
import { onMounted, useState } from "@odoo/owl";

// Backward compatibility for legacy kanban templates invoking kanban_image(...)
patch(KanbanRecord.prototype, {
    kanban_image(model, field, id, cache, default_url) {
        if (this.props?.record) {
            return getImageSrcFromRecordInfo(this.props.record, model, field, id, default_url);
        }
        return id ? `/web/image/${model}/${id}/${field}` : (default_url || "");
    },
});

// Guard against TypeError: Cannot read properties of undefined (reading 'type') in KanbanArchParser
patch(KanbanArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        const modelFields = models?.[modelName]?.fields;
        if (modelFields && xmlDoc && xmlDoc.getElementsByTagName) {
            const fieldNodes = xmlDoc.getElementsByTagName("field");
            for (let i = 0; i < fieldNodes.length; i++) {
                const name = fieldNodes[i].getAttribute("name");
                if (name && !modelFields[name]) {
                    modelFields[name] = {
                        name,
                        type: "char",
                        string: name,
                    };
                }
            }
        }
        return super.parse(xmlDoc, models, modelName);
    },
});

const SCHOOL_APP_XMLID = "school_management.menu_school_root";
const SCHOOL_DASHBOARD_XMLID = "school_management.action_school_dashboard_shell";
const TEACHER_ACTION_XMLID = "school_management.action_teacher_dashboard_shell";
const SCHEDULE_ACTION_XMLID = "school_management.action_university_schedule_view";
const STUDENT_ACTION_XMLID = "school_management.action_student_dashboard_shell";
const SCHOOL_DASHBOARD_TAG = "school_dashboard_shell";
const TEACHER_DASHBOARD_TAG = "teacher_dashboard_shell";
const SCHEDULE_ACTION_TAG = "university_schedule_view";
const STUDENT_DASHBOARD_TAG = "student_dashboard_shell";
const STUDENT_GROUP_XMLID = "school_management.group_school_student";
const STAFF_GROUP_XMLID = "school_management.group_school_teacher";

const SCHOOL_ACTION_XMLIDS = new Set([
    SCHOOL_DASHBOARD_XMLID,
    STUDENT_ACTION_XMLID,
    TEACHER_ACTION_XMLID,
    SCHEDULE_ACTION_XMLID,
    "school_management.action_university_attendance_session",
    "school_management.action_university_attendance_grid",
    "school_management.action_university_attendance_at_risk",
    "school_management.action_university_attendance_comparison",
    "school_management.action_university_staff_attendance_sheet",
    "school_management.action_university_course_registration_student",
    "school_management.action_university_course_evaluation_student_open",
    "school_management.action_university_course_evaluation_student",
    "school_management.action_university_student_change_request_student",
    "school_management.action_university_service_request_student",
]);

const STUDENT_SAFE_ACTION_XMLIDS = new Set([
    STUDENT_ACTION_XMLID,
    SCHEDULE_ACTION_XMLID,
    "school_management.action_university_course_registration_student",
    "school_management.action_university_course_evaluation_student_open",
    "school_management.action_university_course_evaluation_student",
    "school_management.action_university_student_change_request_student",
    "school_management.action_university_service_request_student",
    "school_management.action_university_assignment_my",
    "school_management.action_university_assignment_submission_student",
    "school_management.action_university_attendance_student",
    "school_management.action_university_class_section_student",
    "school_management.action_university_curriculum_student",
    "school_management.action_university_report_card_student",
    "school_management.action_university_transcript_student",
    "school_management.action_university_transcript_request_student",
    "school_management.action_university_notice_board",
]);
const SCHOOL_ACTION_TAGS = new Set([
    SCHOOL_DASHBOARD_TAG,
    STUDENT_DASHBOARD_TAG,
    TEACHER_DASHBOARD_TAG,
    SCHEDULE_ACTION_TAG,
    "university_attendance_sheet",
    "university_attendance_grid",
    "university_attendance_at_risk",
    "university_attendance_comparison",
    "university_staff_attendance_sheet",
]);
const SCHOOL_MODELS = new Set([
    "school.dashboard",
    "university.academic.assignment",
    "university.academic.year",
    "university.assessment.result",
    "university.assignment",
    "university.assignment.submission",
    "university.attendance",
    "university.attendance.session",
    "university.attendance.take.wizard",
    "university.attendance.take.wizard.line",
    "university.attendance.print.wizard",
    "university.staff.attendance",
    "university.bulk.enrollment.wizard",
    "university.capability",
    "university.class.section",
    "university.classroom",
    "university.department",
    "university.document.signature",
    "university.enrollment",
    "university.faculty",
    "university.fee",
    "university.payment",
    "university.program",
    "university.report.card",
    "university.semester",
    "university.semester.subject",
    "university.student",
    "university.student.enrollment.wizard",
    "university.subject",
    "university.teacher",
    "university.timetable.slot",
    "university.transcript",
    "university.transcript.request",
    "university.transcript.request.reject.wizard",
    "university.exam",
    "university.exam.score",
    "university.course.registration",
    "university.course.registration.line",
    "university.course.evaluation",
    "university.student.change.request",
    "university.service.request",
    "university.service.request.line",
    "university.fee.payment.wizard",
]);
const STUDENT_SAFE_ACTION_TAGS = new Set([STUDENT_DASHBOARD_TAG, SCHEDULE_ACTION_TAG]);
const STUDENT_SAFE_MODELS = new Set([
    "university.student",
    "university.enrollment",
    "university.fee",
    "university.fee.line",
    "university.payment",
    "university.assignment",
    "university.assignment.submission",
    "university.assessment.result",
    "university.attendance",
    "university.report.card",
    "university.report.card.line",
    "university.timetable.slot",
    "university.transcript",
    "university.transcript.line",
    "university.transcript.request",
    "university.exam",
    "university.exam.score",
    "university.notice.board",
    "university.service.hour",
    "university.class.section",
    "university.classroom",
    "university.program",
    "university.subject",
    "university.curriculum",
    "university.curriculum.line",
    "university.course.registration",
    "university.course.registration.line",
    "university.course.evaluation",
    "university.student.change.request",
    "university.service.request",
    "university.service.request.line",
    "university.fee.payment.wizard",
    "university.faculty",
    "university.department",
    "university.academic.year",
    "university.semester",
    "university.semester.subject",
    "university.timeslot",
    "university.student.followup",
    "public.holiday",
]);

function debugNavigation(...args) {
    if (window.odoo?.debug) {
        console.debug(...args);
    }
}

function hasLoadedAction(action = {}) {
    return Boolean(action.type || action.res_model || action.tag || action.xml_id || action.id);
}

function isSchoolModel(model) {
    return (
        SCHOOL_MODELS.has(model) ||
        model === "school.dashboard" ||
        (typeof model === "string" && model.startsWith("university."))
    );
}

function isSchoolAction(action = {}) {
    return Boolean(
        isSchoolModel(action.res_model) ||
        SCHOOL_ACTION_TAGS.has(action.tag) ||
        SCHOOL_ACTION_XMLIDS.has(action.xml_id)
    );
}

patch(WebClient.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
        this.schoolState = useState({ isActive: false });
        this.studentRedirecting = false;

        const checkSchoolApp = async () => {
            const currentApp = this.menuService.getCurrentApp();
            const currentAction = this.actionService.currentController?.action || {};
            const actionLoaded = hasLoadedAction(currentAction);
            const schoolAction = isSchoolAction(currentAction);
            const routeAction = router.current.action;
            const schoolRouteWithoutAction =
                !actionLoaded && !routeAction && currentApp?.xmlid === SCHOOL_APP_XMLID;

            this.schoolState.isActive = Boolean(schoolAction || schoolRouteWithoutAction);

            document.body.classList.toggle(
                "o_school_management_active",
                this.schoolState.isActive
            );

            debugNavigation("[University WebClient] layout state", {
                app: currentApp?.xmlid,
                action: currentAction.xml_id || currentAction.tag || currentAction.id,
                model: currentAction.res_model,
                enabled: this.schoolState.isActive,
            });
        };

        const refreshSchoolRoute = async () => {
            await checkSchoolApp();
            await this.redirectStudentToDashboard();
        };

        useBus(this.env.bus, "MENUS:APP-CHANGED", async () => {
            await checkSchoolApp();
            await this.ensureSchoolDashboardRoute();
            await this.redirectStudentToDashboard();
        });
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", refreshSchoolRoute);
        onMounted(() => {
            setTimeout(() => checkSchoolApp());
            setTimeout(() => this.ensureSchoolDashboardRoute());
            setTimeout(() => this.redirectStudentToDashboard());
        });
        checkSchoolApp();
    },

    async ensureSchoolDashboardRoute() {
        if (this.dashboardRedirecting) {
            return;
        }

        const currentApp = this.menuService.getCurrentApp();
        if (currentApp?.xmlid !== SCHOOL_APP_XMLID) {
            return;
        }

        const currentAction = this.actionService.currentController?.action || {};
        const routeAction = router.current.action;
        const actionName = (currentAction.name || "").toLowerCase();
        const actionLoaded = hasLoadedAction(currentAction);
        const isDashboardAction =
            currentAction.tag === SCHOOL_DASHBOARD_TAG ||
            currentAction.xml_id === SCHOOL_DASHBOARD_XMLID ||
            currentAction.tag === TEACHER_DASHBOARD_TAG ||
            currentAction.xml_id === TEACHER_ACTION_XMLID ||
            currentAction.tag === STUDENT_DASHBOARD_TAG ||
            currentAction.xml_id === STUDENT_ACTION_XMLID ||
            currentAction.res_model === "school.dashboard" ||
            actionName.includes("dashboard");

        debugNavigation("[University WebClient] route check", {
            app: currentApp?.xmlid,
            currentAction: currentAction.xml_id || currentAction.tag || currentAction.id,
            routeAction,
            actionLoaded,
        });

        // A real loaded action or an explicit dashboard action owns the route.
        if (isDashboardAction || actionLoaded) {
            const isStudent = await user.hasGroup(STUDENT_GROUP_XMLID);
            const isAdminOrLeadership =
                (await user.hasGroup("base.group_system")) ||
                (await user.hasGroup("school_management.group_school_admin")) ||
                (await user.hasGroup("school_management.group_school_registrar")) ||
                (await user.hasGroup("school_management.group_school_hod")) ||
                (await user.hasGroup("school_management.group_school_dean"));
            const isStaff = (await user.hasGroup(STAFF_GROUP_XMLID)) ||
                            (await user.hasGroup("school_management.group_school_admin")) ||
                            (await user.hasGroup("base.group_system")) ||
                            (await user.hasGroup("school_management.group_school_registrar"));
            if (
                isAdminOrLeadership &&
                (currentAction.tag === TEACHER_DASHBOARD_TAG || currentAction.xml_id === TEACHER_ACTION_XMLID)
            ) {
                await this.actionService.doAction(SCHOOL_DASHBOARD_XMLID, { clearBreadcrumbs: true });
                return;
            }
            if (isStudent && !isStaff) {
                if (currentAction.tag === SCHOOL_DASHBOARD_TAG || currentAction.xml_id === SCHOOL_DASHBOARD_XMLID) {
                    await this.actionService.doAction(STUDENT_ACTION_XMLID, { clearBreadcrumbs: true });
                    return;
                }
            }
            return;
        }

        this.dashboardRedirecting = true;
        try {
            const isAdminOrLeadership =
                (await user.hasGroup("base.group_system")) ||
                (await user.hasGroup("school_management.group_school_admin")) ||
                (await user.hasGroup("school_management.group_school_registrar")) ||
                (await user.hasGroup("school_management.group_school_hod")) ||
                (await user.hasGroup("school_management.group_school_dean"));
            const isTeacher =
                (await user.hasGroup("school_management.group_school_teacher")) ||
                (await user.hasGroup("school_management.group_university_teacher"));
            const isStudent = await user.hasGroup(STUDENT_GROUP_XMLID);

            let targetAction = SCHOOL_DASHBOARD_XMLID;
            if (isStudent && !isAdminOrLeadership && !isTeacher) {
                targetAction = STUDENT_ACTION_XMLID;
            } else if (isTeacher && !isAdminOrLeadership) {
                targetAction = TEACHER_ACTION_XMLID;
            }

            debugNavigation("[University WebClient] opening Dashboard", {
                action: targetAction,
            });
            await this.actionService.doAction(targetAction, {
                clearBreadcrumbs: true,
            });
        } finally {
            this.dashboardRedirecting = false;
        }
    },

    async redirectStudentToDashboard() {
        if (this.studentRedirecting) {
            return;
        }
        if (!(await user.hasGroup(STUDENT_GROUP_XMLID))) {
            return;
        }
        // A dual-role user can intentionally switch between staff and student
        // views; only student-only users need automatic dashboard redirection.
        if (await user.hasGroup(STAFF_GROUP_XMLID)) {
            return;
        }

        const currentApp = this.menuService.getCurrentApp();
        const currentAction = this.actionService.currentController?.action || {};
        const actionLoaded = hasLoadedAction(currentAction);
        const routeAction = router.current.action;
        const inSchoolRoute = isSchoolAction(currentAction) ||
            (!actionLoaded && !routeAction && currentApp?.xmlid === SCHOOL_APP_XMLID);

        if (!inSchoolRoute) {
            return;
        }

        if (currentAction.type === "ir.actions.report" || currentAction.type === "ir.actions.act_url") {
            return;
        }

        // Students must never view the executive university dashboard
        if (currentAction.tag === SCHOOL_DASHBOARD_TAG || currentAction.xml_id === SCHOOL_DASHBOARD_XMLID) {
            this.studentRedirecting = true;
            try {
                await this.actionService.doAction(STUDENT_ACTION_XMLID, {
                    clearBreadcrumbs: true,
                });
            } finally {
                this.studentRedirecting = false;
            }
            return;
        }

        const actionModel = currentAction.res_model;
        const isStudentSafeAction =
            STUDENT_SAFE_ACTION_TAGS.has(currentAction.tag) ||
            STUDENT_SAFE_MODELS.has(actionModel) ||
            STUDENT_SAFE_ACTION_XMLIDS.has(currentAction.xml_id);

        if (isStudentSafeAction) {
            return;
        }

        this.studentRedirecting = true;
        try {
            await this.actionService.doAction(STUDENT_ACTION_XMLID, {
                clearBreadcrumbs: true,
            });
        } finally {
            this.studentRedirecting = false;
        }
    },
});
