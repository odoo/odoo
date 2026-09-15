"""Transfer booking ownership without replacing records or trusting old conference URLs."""

from odoo.db.schema import column_exists, create_column
from odoo.tools import SQL

XMLIDS = {
    "appointment.res_groups_privilege_appointment": "calendar.res_groups_privilege_appointment",
    "appointment.group_appointment_user": "calendar.group_appointment_user",
    "appointment.group_appointment_manager": "calendar.group_appointment_manager",
    "appointment.appointment_type_rule_internal": "calendar.appointment_type_rule_internal",
    "appointment.appointment_type_rule_internal_published": "calendar.appointment_type_rule_internal_published",
    "appointment.appointment_type_rule_user": "calendar.appointment_type_rule_user",
    "appointment.appointment_type_rule_user_write_unlink": "calendar.appointment_type_rule_user_write_unlink",
    "appointment.appointment_type_rule_admin": "calendar.appointment_type_rule_admin",
    "appointment.appointment_slot_rule_internal": "calendar.appointment_slot_rule_internal",
    "appointment.appointment_slot_rule_internal_published": "calendar.appointment_slot_rule_internal_published",
    "appointment.appointment_slot_rule_user": "calendar.appointment_slot_rule_user",
    "appointment.appointment_slot_rule_user_write_unlink": "calendar.appointment_slot_rule_user_write_unlink",
    "appointment.appointment_slot_rule_admin": "calendar.appointment_slot_rule_admin",
    "appointment.appointment_invite_rule_user_internal": "calendar.appointment_invite_rule_user_internal",
    "appointment.appointment_invite_rule_user_internal_write_unlink": "calendar.appointment_invite_rule_user_internal_write_unlink",
    "appointment.appointment_invite_rule_admin": "calendar.appointment_invite_rule_admin",
    "appointment.appointment_answer_input_rule_internal": "calendar.appointment_answer_input_rule_internal",
    "appointment.appointment_answer_input_rule_internal_published": "calendar.appointment_answer_input_rule_internal_published",
    "appointment.appointment_answer_input_rule_user": "calendar.appointment_answer_input_rule_user",
    "appointment.appointment_answer_input_rule_admin": "calendar.appointment_answer_input_rule_admin",
    "appointment.appointment_booking_line_rule_internal": "calendar.appointment_booking_line_rule_internal",
    "appointment.appointment_booking_line_rule_internal_published": "calendar.appointment_booking_line_rule_internal_published",
    "appointment.appointment_booking_line_rule_user": "calendar.appointment_booking_line_rule_user",
    "appointment.appointment_booking_line_rule_admin": "calendar.appointment_booking_line_rule_admin",
    "appointment.resource_schedule_exception_rule_appointment_manager": "calendar.resource_schedule_exception_rule_appointment_manager",
    "appointment.appointment_response_rule_internal": "calendar.appointment_response_rule_internal",
    "appointment.appointment_response_rule_internal_published": "calendar.appointment_response_rule_internal_published",
    "appointment.appointment_response_rule_user": "calendar.appointment_response_rule_user",
    "appointment.appointment_response_rule_admin": "calendar.appointment_response_rule_admin",
    "appointment.survey_question_rule_appointment_reader": "calendar.survey_question_rule_appointment_reader",
    "appointment.survey_question_rule_appointment_manager": "calendar.survey_question_rule_appointment_manager",
    "appointment.survey_question_answer_rule_appointment_reader": "calendar.survey_question_answer_rule_appointment_reader",
    "appointment.survey_question_answer_rule_appointment_manager": "calendar.survey_question_answer_rule_appointment_manager",
    "appointment.appointment_response_read_boundary": "calendar.appointment_response_read_boundary",
    "appointment.appointment_response_edit_boundary": "calendar.appointment_response_edit_boundary",
    "appointment.appointment_response_line_read_boundary": "calendar.appointment_response_line_read_boundary",
    "appointment.appointment_response_line_edit_boundary": "calendar.appointment_response_line_edit_boundary",
    "appointment.appointment_question_edit_boundary": "calendar.appointment_question_edit_boundary",
    "appointment.appointment_choice_edit_boundary": "calendar.appointment_choice_edit_boundary",
    "appointment.mt_calendar_event_booked": "calendar.mt_calendar_event_booked",
    "appointment.mt_calendar_event_canceled": "calendar.mt_calendar_event_canceled",
    "appointment.mt_appointment_type_booked": "calendar.mt_appointment_type_booked",
    "appointment.mt_appointment_type_canceled": "calendar.mt_appointment_type_canceled",
    "appointment.appointment_booked_mail_template": "calendar.appointment_booked_mail_template",
    "appointment.appointment_canceled_mail_template": "calendar.appointment_canceled_mail_template",
    "appointment.attendee_invitation_mail_template": "calendar.attendee_invitation_mail_template",
    "appointment.res_partner_appointment_type_dental_care": "calendar.res_partner_appointment_type_dental_care",
    "appointment.res_partner_appointment_type_tennis_court": "calendar.res_partner_appointment_type_tennis_court",
    "appointment.appointment_question_phone": "calendar.appointment_question_phone",
    "appointment.appointment_type_dental_care": "calendar.appointment_type_dental_care",
    "appointment.appointment_type_dental_care_question_1": "calendar.appointment_type_dental_care_question_1",
    "appointment.appointment_type_tennis_court": "calendar.appointment_type_tennis_court",
    "appointment.appointment_default_resource_calendar": "calendar.appointment_default_resource_calendar",
    "appointment.appointment_type_tennis_court_resource_1": "calendar.appointment_type_tennis_court_resource_1",
    "appointment.appointment_type_tennis_court_resource_2": "calendar.appointment_type_tennis_court_resource_2",
    "appointment.appointment_type_tennis_court_resource_3": "calendar.appointment_type_tennis_court_resource_3",
    "appointment.appointment_type_tennis_court_resource_4": "calendar.appointment_type_tennis_court_resource_4",
    "appointment.appointment_manage_leaves_view_form": "calendar.appointment_manage_leaves_view_form",
    "appointment.appointments_list_layout": "calendar.appointments_list_layout",
    "appointment.appointment_type_select": "calendar.appointment_type_select",
    "appointment.appointment_progress_bar": "calendar.appointment_progress_bar",
    "appointment.appointment_info": "calendar.appointment_info",
    "appointment.staff_user_select": "calendar.staff_user_select",
    "appointment.appointment_calendar": "calendar.appointment_calendar",
    "appointment.appointment_edit_in_backend": "calendar.appointment_edit_in_backend",
    "appointment.appointment_details_column": "calendar.appointment_details_column",
    "appointment.appointment_meeting_details": "calendar.appointment_meeting_details",
    "appointment.appointment_meeting_user": "calendar.appointment_meeting_user",
    "appointment.appointment_meeting_date": "calendar.appointment_meeting_date",
    "appointment.resource_schedule_exception_action_show_appointment_resources": "calendar.resource_schedule_exception_action_show_appointment_resources",
    "appointment.appointment_slot_view_form": "calendar.appointment_slot_view_form",
    "appointment.appointment_menu_calendar": "calendar.appointment_menu_calendar",
    "appointment.reporting_menu_calendar": "calendar.reporting_menu_calendar",
    "appointment.appointment_answer_input_view_search": "calendar.appointment_answer_input_view_search",
    "appointment.appointment_answer_input_view_form": "calendar.appointment_answer_input_view_form",
    "appointment.appointment_answer_input_view_tree": "calendar.appointment_answer_input_view_tree",
    "appointment.appointment_answer_input_view_graph": "calendar.appointment_answer_input_view_graph",
    "appointment.appointment_answer_input_view_pivot": "calendar.appointment_answer_input_view_pivot",
    "appointment.appointment_answer_input_action": "calendar.appointment_answer_input_action",
    "appointment.appointment_answer_input_action_list": "calendar.appointment_answer_input_action_list",
    "appointment.appointment_answer_input_action_graph": "calendar.appointment_answer_input_action_graph",
    "appointment.appointment_answer_input_action_pivot": "calendar.appointment_answer_input_action_pivot",
    "appointment.appointment_answer_input_action_form": "calendar.appointment_answer_input_action_form",
    "appointment.appointment_question_view_search": "calendar.appointment_question_view_search",
    "appointment.appointment_question_view_form": "calendar.appointment_question_view_form",
    "appointment.appointment_question_view_list": "calendar.appointment_question_view_list",
    "appointment.appointment_question_action": "calendar.appointment_question_action",
    "appointment.appointment_form": "calendar.appointment_form",
    "appointment.appointment_type_view_search": "calendar.appointment_type_view_search",
    "appointment.appointment_type_view_kanban": "calendar.appointment_type_view_kanban",
    "appointment.appointment_type_view_tree": "calendar.appointment_type_view_tree",
    "appointment.appointment_type_view_form": "calendar.appointment_type_view_form",
    "appointment.appointment_type_view_form_add_simplified": "calendar.appointment_type_view_form_add_simplified",
    "appointment.appointment_type_view_form_custom_share": "calendar.appointment_type_view_form_custom_share",
    "appointment.appointment_type_action": "calendar.appointment_type_action",
    "appointment.appointment_invite_view_search": "calendar.appointment_invite_view_search",
    "appointment.appointment_invite_view_tree": "calendar.appointment_invite_view_tree",
    "appointment.appointment_invite_view_form": "calendar.appointment_invite_view_form",
    "appointment.appointment_invite_view_form_insert_link": "calendar.appointment_invite_view_form_insert_link",
    "appointment.appointment_invite_action": "calendar.appointment_invite_action",
    "appointment.appointment_invite_action_stat": "calendar.appointment_invite_action_stat",
    "appointment.calendar_alarm_view_form": "calendar.calendar_alarm_view_form_booking",
    "appointment.portal_my_home_menu_appointment": "calendar.portal_my_home_menu_appointment",
    "appointment.portal_my_home_appointment": "calendar.portal_my_home_appointment",
    "appointment.portal_my_appointments": "calendar.portal_my_appointments",
    "appointment.calendar_event_view_form": "calendar.calendar_event_view_form",
    "appointment.calendar_event_view_tree": "calendar.calendar_event_view_tree",
    "appointment.calendar_event_view_search": "calendar.calendar_event_view_search",
    "appointment.calendar_event_view_search_booking": "calendar.calendar_event_view_search_booking",
    "appointment.calendar_event_view_tree_booking": "calendar.calendar_event_view_tree_booking",
    "appointment.calendar_event_view_form_gantt_booking": "calendar.calendar_event_view_form_gantt_booking",
    "appointment.calendar_event_view_gantt_kanban_popover": "calendar_gantt.calendar_event_view_gantt_kanban_popover",
    "appointment.calendar_event_view_gantt_booking_resource": "calendar_gantt.calendar_event_view_gantt_booking_resource",
    "appointment.calendar_event_view_gantt_booking_user": "calendar_gantt.calendar_event_view_gantt_booking_user",
    "appointment.calendar_event_view_calendar": "calendar.calendar_event_view_calendar",
    "appointment.calendar_event_view_calendar_booking_resource": "calendar.calendar_event_view_calendar_booking_resource",
    "appointment.calendar_event_action_view_bookings_resources": "calendar.calendar_event_action_view_bookings_resources",
    "appointment.calendar_event_action_view_bookings_users": "calendar.calendar_event_action_view_bookings_users",
    "appointment.calendar_event_action_all_resources_bookings": "calendar.calendar_event_action_all_resources_bookings",
    "appointment.calendar_event_action_all_users_appointments": "calendar.calendar_event_action_all_users_appointments",
    "appointment.calendar_event_view_graph": "calendar.calendar_event_view_graph",
    "appointment.calendar_event_view_pivot": "calendar.calendar_event_view_pivot",
    "appointment.calendar_event_action_report_all": "calendar.calendar_event_action_report_all",
    "appointment.calendar_event_action_appointment_reporting": "calendar.calendar_event_action_appointment_reporting",
    "appointment.appointment_answer_view_form": "calendar.appointment_answer_view_form",
    "appointment.appointment_resource_view_search": "calendar.appointment_resource_view_search",
    "appointment.appointment_resource_view_form": "calendar.appointment_resource_view_form",
    "appointment.appointment_resource_view_tree": "calendar.appointment_resource_view_tree",
    "appointment.appointment_resource_action": "calendar.appointment_resource_action",
    "appointment.appointment_resource_action_stat": "calendar.appointment_resource_action_stat",
    "appointment.main_menu_appointments": "calendar.main_menu_appointments",
    "appointment.menu_appointment_schedule_resources": "calendar.menu_appointment_schedule_resources",
    "appointment.menu_appointment_schedule_resource_booking": "calendar.menu_appointment_schedule_resource_booking",
    "appointment.menu_appointment_schedule_staff_appointment": "calendar.menu_appointment_schedule_staff_appointment",
    "appointment.appointment_type_menu": "calendar.appointment_type_menu",
    "appointment.menu_appointment_invite": "calendar.menu_appointment_invite",
    "appointment.menu_appointment_reporting": "calendar.menu_appointment_reporting",
    "appointment.menu_appointment_reporting_bookings": "calendar.menu_appointment_reporting_bookings",
    "appointment.menu_appointment_reporting_answers": "calendar.menu_appointment_reporting_answers",
    "appointment.appointment_menu_config": "calendar.appointment_menu_config",
    "appointment.menu_appointment_questions": "calendar.menu_appointment_questions",
    "appointment.menu_appointment_reminders": "calendar.menu_appointment_reminders",
    "appointment.menu_appointment_resource": "calendar.menu_appointment_resource",
    "appointment.menu_appointment_resource_leaves": "calendar.menu_appointment_resource_leaves",
    "appointment.appointment_validated": "calendar.appointment_validated",
    "appointment.appointment_validated_card": "calendar.appointment_validated_card",
    "appointment.resources_list": "calendar.booking.resources_list",
    "appointment.resources_capacity_options": "calendar.booking.resources_capacity_options",
    "appointment.slots_list": "calendar.booking.slots_list",
    "appointment.BadgeSelectionIconMappingField": "calendar.booking.BadgeSelectionIconMappingField",
    "appointment.AppointmentBookingGanttRendererControls": "calendar.booking.AppointmentBookingGanttRendererControls",
    "appointment.AppointmentBookingGanttController": "calendar.booking.AppointmentBookingGanttController",
    "appointment.AppointmentBookingGanttRendererPill": "calendar.booking.AppointmentBookingGanttRendererPill",
    "appointment.GanttPopover": "calendar.booking.GanttPopover",
    "appointment.CalendarController": "calendar.booking.CalendarController",
    "appointment.AppointmentTypeKanbanRenderer": "calendar.booking.AppointmentTypeKanbanRenderer",
    "appointment.AppointmentBookingListRenderer": "calendar.booking.AppointmentBookingListRenderer",
    "appointment.AppointmentTypeListRenderer": "calendar.booking.AppointmentTypeListRenderer",
    "appointment.FormViewDialog.buttons": "calendar.booking.FormViewDialog.buttons",
    "appointment.AppointmentSyncButton": "calendar.booking.AppointmentSyncButton",
    "appointment.AppointmentTypeActionHelper": "calendar.booking.AppointmentTypeActionHelper",
    "appointment.AppointmentTypeSyncDuration": "calendar.booking.AppointmentTypeSyncDuration",
    "appointment.appointmentQuickShareButton": "calendar.booking.appointmentQuickShareButton",
    "appointment.AppointmentBookingActionHelper": "calendar.booking.AppointmentBookingActionHelper",
    "appointment.AppointmentTemplatePickerDialog": "calendar.booking.AppointmentTemplatePickerDialog",
    "appointment.AppointmentTemplateCard": "calendar.booking.AppointmentTemplateCard",
    "appointment.AppointmentInviteCopyClose": "calendar.booking.AppointmentInviteCopyClose",
    "appointment.access_appointment_type_all": "calendar.access_appointment_type_all",
    "appointment.access_appointment_type_user": "calendar.access_appointment_type_user",
    "appointment.access_appointment_type_apt_user": "calendar.access_appointment_type_apt_user",
    "appointment.access_appointment_type_manager": "calendar.access_appointment_type_manager",
    "appointment.access_appointment_slot_user": "calendar.access_appointment_slot_user",
    "appointment.access_appointment_slot_apt_user": "calendar.access_appointment_slot_apt_user",
    "appointment.access_appointment_slot_manager": "calendar.access_appointment_slot_manager",
    "appointment.access_appointment_question_employee": "calendar.access_appointment_question_employee",
    "appointment.access_appointment_question_manager": "calendar.access_appointment_question_manager",
    "appointment.access_appointment_question_answer_employee": "calendar.access_appointment_question_answer_employee",
    "appointment.access_appointment_question_answer_manager": "calendar.access_appointment_question_answer_manager",
    "appointment.access_appointment_question_answer_input_user": "calendar.access_appointment_question_answer_input_user",
    "appointment.access_appointment_question_answer_input_manager": "calendar.access_appointment_question_answer_input_manager",
    "appointment.access_calendar_alarm_public": "calendar.access_calendar_alarm_public",
    "appointment.access_calendar_alarm_portal": "calendar.access_calendar_alarm_portal",
    "appointment.access_calendar_alarm_employee": "calendar.access_calendar_alarm_employee",
    "appointment.access_appointment_invite_user": "calendar.access_appointment_invite_user",
    "appointment.access_appointment_invite_apt_user": "calendar.access_appointment_invite_apt_user",
    "appointment.access_appointment_invite_manager": "calendar.access_appointment_invite_manager",
    "appointment.access_appointment_manage_leaves_all": "calendar.access_appointment_manage_leaves_all",
    "appointment.access_appointment_manage_leaves_manager": "calendar.access_appointment_manage_leaves_manager",
    "appointment.access_appointment_resource_manager": "calendar.access_appointment_resource_manager",
    "appointment.access_appointment_resource_user": "calendar.access_appointment_resource_user",
    "appointment.access_appointment_resource_all": "calendar.access_appointment_resource_all",
    "appointment.access_appointment_booking_line_manager": "calendar.access_appointment_booking_line_manager",
    "appointment.access_appointment_booking_line_user": "calendar.access_appointment_booking_line_user",
    "appointment.access_appointment_booking_line_all": "calendar.access_appointment_booking_line_all",
    "appointment.access_resource_resource_appointment_manager": "calendar.access_resource_resource_appointment_manager",
    "appointment.access_appointment_response_user": "calendar.access_appointment_response_user",
    "appointment.access_appointment_response_manager": "calendar.access_appointment_response_manager",
    "appointment.model_ir_ui_view": "calendar_gantt.model_ir_ui_view",
    "appointment.field_ir_ui_view__display_name": "calendar_gantt.field_ir_ui_view__display_name",
    "appointment.field_ir_ui_view__id": "calendar_gantt.field_ir_ui_view__id",
}


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        CREATE TABLE calendar_booking_upgrade_view_custom AS
        SELECT custom.* FROM ir_ui_view_custom custom
        JOIN ir_model_data data ON data.model = 'ir.ui.view' AND data.res_id = custom.ref_id
        WHERE data.module = 'appointment'
    """)
    cr.execute(
        "SELECT name, model, res_id FROM ir_model_data WHERE module = 'appointment'"
    )
    xmlids = dict(XMLIDS)
    for old_name, model, res_id in cr.fetchall():
        target = XMLIDS.get("appointment." + old_name, "calendar." + old_name)
        xmlids["appointment." + old_name] = target
        module, name = target.split(".", 1)
        cr.execute(
            "SELECT id, model, res_id FROM ir_model_data WHERE module = %s AND name = %s",
            (module, name),
        )
        existing = cr.fetchone()
        if existing:
            if existing[1:] != (model, res_id):
                raise ValueError(
                    f"Cannot transfer appointment.{old_name}: {target} owns a different record"
                )
            cr.execute(
                "DELETE FROM ir_model_data WHERE module = 'appointment' AND name = %s",
                (old_name,),
            )
        else:
            cr.execute(
                "UPDATE ir_model_data SET module = %s, name = %s WHERE module = 'appointment' AND name = %s",
                (module, name, old_name),
            )

    # Rewrite only known external identifiers, never Python model names such as
    # appointment.type, nor variables named appointment in custom expressions.
    for table, column, jsonb in (
        ("ir_ui_view", "arch_db", True),
        ("calendar_booking_upgrade_view_custom", "arch", False),
        ("ir_act_window", "context", False),
        ("ir_act_window", "domain", False),
        ("ir_filters", "context", False),
        ("ir_filters", "domain", False),
        ("ir_act_server", "code", False),
        ("mail_template", "body_html", True),
    ):
        for old, new in sorted(xmlids.items(), key=lambda item: -len(item[0])):
            # PostgreSQL word boundaries prevent prefix matches on longer ids.
            pattern = r"\m" + old.replace(".", r"\.") + r"\M"
            source = (
                SQL("%s::text", SQL.identifier(column))
                if jsonb
                else SQL.identifier(column)
            )
            result = SQL("regexp_replace(%s, %s, %s, 'g')", source, pattern, new)
            if jsonb:
                result = SQL("%s::jsonb", result)
            cr.execute(
                SQL(
                    "UPDATE %s SET %s = %s WHERE %s ~ %s",
                    SQL.identifier(table),
                    SQL.identifier(column),
                    result,
                    source,
                    pattern,
                )
            )

    # Reflection rows have a module FK with ON DELETE CASCADE. Transfer it before
    # deleting the absorbed module so constraints keep their metadata identity.
    for table in ("ir_model_constraint", "ir_model_relation"):
        cr.execute(
            SQL(
                """
            UPDATE %s SET module = (SELECT id FROM ir_module_module WHERE name = 'calendar')
             WHERE module = (SELECT id FROM ir_module_module WHERE name = 'appointment')
        """,
                SQL.identifier(table),
            )
        )

    # Removing the obsolete module is metadata cleanup, never an uninstall.
    cr.execute("DELETE FROM ir_module_module_dependency WHERE name = 'appointment'")
    cr.execute("DELETE FROM ir_module_module WHERE name = 'appointment'")
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'base' AND name = 'module_appointment'"
    )

    # A Char callable default is evaluated once when backfilling a new column.
    # Generate per row before ORM initialization to avoid shared capabilities.
    if not column_exists(cr, "calendar_event", "booking_access_token"):
        create_column(cr, "calendar_event", "booking_access_token", "varchar")
    if column_exists(cr, "calendar_event", "appointment_type_id"):
        cr.execute(
            "UPDATE calendar_event SET booking_access_token = gen_random_uuid()::text WHERE appointment_type_id IS NOT NULL AND booking_access_token IS NULL"
        )
