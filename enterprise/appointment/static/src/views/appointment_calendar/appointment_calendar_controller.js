/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { rpc } from "@web/core/network/rpc";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, useSubEnv, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { user } from "@web/core/user";
import { CustomAppointmentFormViewDialog } from "../custom_appointment_form_dialog/custom_appointment_form_dialog";

patch(AttendeeCalendarController, {
    components: { ...AttendeeCalendarController.components, Dropdown },
});

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);
        this.popover = usePopover(Tooltip, { position: "bottom" });
        this.copyLinkRef = useRef("copyLinkRef");
        this.orm = useService("orm");

        this.appointmentState = useState({
            data: {},
            lastAppointment: false,
        });

        useSubEnv({
            calendarState: useState({
                mode: "default",
            }),
        });

        onWillStart(async () => {
            this.appointmentState.data = await rpc(
                "/appointment/appointment_type/get_staff_user_appointment_types"
            );
            this.isAppointmentUser = await user.hasGroup("appointment.group_appointment_user");
        });
    },

    async _createCustomAppointmentType() {
        const customAppointment = await rpc(
            "/appointment/appointment_type/create_custom",
            {
                slots: this._getSlots(),
                context: this.props.context, // This allows to propagate keys like default_opportunity_id / default_applicant_id
            },
        );
        if (customAppointment.appointment_type_id) {
            this.appointmentState.lastAppointment = {
                'id': customAppointment.appointment_type_id,
                'isCustom': true,
                'url': customAppointment.invite_url,
                'viewId': customAppointment.view_id,
            }
        }
    },

    /**
     * Returns whether we have slot events.
     */
    hasSlotEvents() {
        return Object.keys(this.model.data.slots).length;
    },

    _getSlots() {
        return Object.values(this.model.data.slots).map(slot => ({
            start: serializeDateTime(slot.start),
            end: serializeDateTime(slot.start === slot.end ? slot.end.plus({ days: 1 }) : slot.end), //TODO: check if necessary
            allday: slot.isAllDay,
        }));
    },

    async _updateCustomAppointmentSlots() {
        await rpc(
            "/appointment/appointment_type/update_custom",
            {
                appointment_type_id: this.appointmentState.lastAppointment.id,
                slots: this._getSlots(),
            },
        );
    },

    _writeUrlToClipboard() {
        if (!this.appointmentState.lastAppointment) {
            return;
        }
        setTimeout(async () => await navigator.clipboard.writeText(this.appointmentState.lastAppointment.url));
    },

    onClickCustomLink() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'appointment.invite',
            name: _t('Share Link'),
            views: [[false, 'form']],
            target: 'new',
            context: {
                ...this.props.context,
                dialog_size: 'medium',
            },
        })
    },

    onClickSelectAvailabilities() {
        this.env.calendarState.mode = "slots-creation";
    },

    async onClickGetShareLink() {
        if (!this.appointmentState.lastAppointment) {
            await this._createCustomAppointmentType();
        } else if (this.appointmentState.lastAppointment.isCustom && this.env.calendarState.mode === "slots-creation") {
            await this._updateCustomAppointmentSlots();
        }
        this._writeUrlToClipboard();
        if (!this.copyLinkRef.el) {
            return;
        }
        if (this.appointmentState.lastAppointment.isCustom) {
            this.env.calendarState.mode = "default";
            this.model.clearSlots();
        }
        this.appointmentState.lastAppointment.waitingCopyLinkCustomType = false;
        this.popover.open(this.copyLinkRef.el, { tooltip: _t("Copied!") });
        browser.setTimeout(this.popover.close, 800);
    },

    async onClickOpenForm() {
        if (!this.appointmentState.lastAppointment) {
            await this._createCustomAppointmentType();
        } else if (this.appointmentState.lastAppointment.isCustom && this.env.calendarState.mode === "slots-creation") {
            await this._updateCustomAppointmentSlots();
        }

        if (this.appointmentState.lastAppointment.isCustom) {
            // The url copy paste may be done in the configuration dialog.
            // This is used in order to not display the "Link Copied" message too early.
            this.appointmentState.lastAppointment.waitingCopyLinkCustomType = this.env.calendarState.mode === "slots-creation";
            this.displayDialog(CustomAppointmentFormViewDialog, {
                context: this.props.context,
                inviteUrl: this.appointmentState.lastAppointment.url,
                resId: this.appointmentState.lastAppointment.id,
                resModel: 'appointment.type',
                size: 'md',
                title: _t('Share Availabilities'),
                viewId: this.appointmentState.lastAppointment.viewId,
                onLinkCopied: () => {;
                    this.appointmentState.lastAppointment.waitingCopyLinkCustomType = false;
                    this.env.calendarState.mode = "default";
                    this.model.clearSlots();
                },
            });
        }
        else {
            this.actionService.doAction({
                name: _t('Open Appointment Type Form'),
                type: 'ir.actions.act_window',
                res_model: 'appointment.type',
                views: [[false, 'form']],
                res_id: this.appointmentState.lastAppointment.id,
            });
        }
    },

    onClickDiscard() {
        if (this.env.calendarState.mode === "slots-creation") {
            this.model.clearSlots();
        }
        this.env.calendarState.mode = "default";
        this.appointmentState.lastAppointment = false;
    },

    async onClickSearchCreateAnytimeAppointment() {
        const anytimeAppointment = await rpc("/appointment/appointment_type/search_create_anytime", {
            context: this.props.context,
        });
        if (anytimeAppointment.appointment_type_id) {
            this.appointmentState.lastAppointment = {
                'id': anytimeAppointment.appointment_type_id,
                'url': anytimeAppointment.invite_url,
            }
            this._writeUrlToClipboard();
        }
    },

    async onClickGetAppointmentUrl(appointmentTypeId) {
        const appointment = await rpc("/appointment/appointment_type/get_book_url", {
            appointment_type_id: appointmentTypeId,
            context: this.props.context,
        });
        this.appointmentState.lastAppointment = {
            'id': appointment.appointment_type_id,
            'url': appointment.invite_url,
        }
        this._writeUrlToClipboard();
    },
});
