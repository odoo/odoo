import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;
import { onWillStart } from "@odoo/owl";
import { AppointmentBookingGanttRendererControls } from "./gantt_renderer_controls";

export class AppointmentBookingGanttRenderer extends GanttRenderer {
    static components = {
        ...GanttRenderer.components,
        GanttRendererControls: AppointmentBookingGanttRendererControls,
    }

    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            this.isAppointmentManager = await user.hasGroup("appointment.group_appointment_manager");
        });
    }

    /**
     * @override
     * If multiple columns have been selected, remove the default duration from the context so that
     * the stop matches the end of the selection instead of being redefined to match the appointment duration.
     */
    onCreate(rowId, columnStart, columnStop) {
        const { start, stop } = this.getColumnStartStop(columnStart, columnStop);
        const context = this.model.getDialogContext({rowId, start, stop, withDefault: true});
        if (columnStart != columnStop){
            delete context['default_duration'];
        }
        this.props.create(context);
    }

    /**
     * @override
     */
    enrichPill(pill) {
        const enrichedPill = super.enrichPill(pill);
        const { record } = pill;
        if (!record.appointment_type_id) {
            return enrichedPill;
        }
        const now = DateTime.now();
        // see o-colors-complete for array of colors to index into
        let color = false;
        if (!record.active) {
            color = false;
        } else if (record.appointment_status === 'booked') {
            color = now.diff(record.start, ['minutes']).minutes > 15 ? 2 : 4;  // orange if late ; light blue if not
        } else if (record.appointment_status === 'attended') {
            color = 10;  // green
        } else if (record.appointment_status === 'no_show') {
            color = 1;  // red
        } else if (record.appointment_status === 'request' && record.start < now) {
            color = 2;  // orange (request state has info-decoration)
        } else {
            color = 8;  // blue
        }
        if (color) {
            enrichedPill.className += ` o_gantt_color_${color}`;
        }
        return enrichedPill;
    }

    /**
     * @override
     */
    processRow() {
        const result = super.processRow(...arguments);
        const { isGroup, id: rowId } = result.rows[0];
        if (!isGroup && this.model.metaData.groupedBy.includes("partner_ids")) {
            const { partner_ids } = Object.assign({}, ...JSON.parse(rowId));
            for (const pill of this.rowPills[rowId]) {
                if (partner_ids[0] !== pill.record.partner_id[0]) {
                    pill.className += " o_appointment_booking_gantt_color_grey";
                }
            }
        }
        return result;
    }

    /**
     * Patch the flow so that we will have access to the id of the partner
     * in the row the user originally clicked when writing to reschedule, as originId.
     *
     * @override
     */
    async dragPillDrop({ pill, cell, diff }) {
        let unpatch = null;
        if (this.model.metaData.groupedBy && (this.model.metaData.groupedBy[0] === "partner_ids" || this.model.metaData.groupedBy[0] === "resource_ids")) {
            const originResId = this.rows.find((row) => {
                return this.rowPills[row.id].some(
                    (rowPill) => rowPill.id === this.pills[pill.dataset.pillId].id,
                );
            })?.resId;
            unpatch = patch(this.model, {
                getSchedule() {
                    const schedule = super.getSchedule(...arguments);
                    schedule.originId = originResId;
                    return schedule;
                },
            });
        }
        const ret = super.dragPillDrop(...arguments);
        if (unpatch) {
            unpatch();
        }
        return ret;
    }

    get controlsProps() {
        const showAddLeaveButton = () =>
            this.isAppointmentManager && this.model.metaData.groupedBy[0] === "resource_ids";
        return Object.assign(super.controlsProps, {
            onClickAddLeave: async () => {
                this.env.services.action.doAction(
                    {
                        name: _t("Add Closing Day(s)"),
                        type: "ir.actions.act_window",
                        res_model: "appointment.manage.leaves",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "new",
                        context: {},
                    },
                    { onClose: () => this.model.fetchData() }
                );
            },
            /**
             * Display 'Add Leaves' action button if grouping by appointment resources.
             */
            get showAddLeaveButton() {
                return showAddLeaveButton();
            },
        });
    }

    /**
     * @override
     * Async copy of the overriden method
     */
    async onPillClicked(ev, pill) {
        if (this.popover.isOpen) {
            return;
        }
        const popoverTarget = ev.target.closest(".o_gantt_pill_wrapper");
        this.popover.open(popoverTarget, await this.getPopoverProps(pill));
    }
    /**
     * @override
     */
    async getPopoverProps(pill) {
        const popoverProps = super.getPopoverProps(pill);
        const { record } = pill;
        const partner_ids = record.partner_ids || [];
        let contact_partner_id = false;
        if (record.partner_ids) {
            contact_partner_id = record.partner_id
            ? partner_ids.find(partner_id => partner_id != record.partner_id[0])
            : partner_ids.length ? partner_ids[0] : false;
        }
        const popoverValues = contact_partner_id
            ? await this.orm.read(
                'res.partner',
                [contact_partner_id], ['name', 'email', 'phone']
            )
            : [{
                id: false,
                name: '',
                email: '',
                phone: '',
            }];
        Object.assign(popoverProps, {
            buttons: this.getPopoverButtons(record),
            context: {
                ...popoverProps.context,
                can_edit: this.model.metaData.canEdit,
                gantt_pill_contact_email: popoverValues[0].email,
                gantt_pill_contact_name: popoverValues[0].name,
                gantt_pill_contact_phone: popoverValues[0].phone,
            },
            title: popoverValues[0].name || this.getDisplayName(pill),
        });
        return popoverProps;
    }

    getPopoverButtons(record) {
        return [{
            class: "o_appointment_booking_confirm_status btn btn-sm btn-primary",
            onClick: () => {
                if (this.model.metaData.canEdit && record.appointment_status) {
                    const newAppointmentStatus = document.querySelector('.o_appointment_booking_status').selectedOptions[0].value;
                    this.orm.write("calendar.event", [record.id], {
                        active: newAppointmentStatus !== 'cancelled',
                        appointment_status: newAppointmentStatus,
                    }).then(() => this.model.fetchData());
                }
            },
            text: this.model.metaData.canEdit && record.appointment_status ? _t("Save & Close") : _t('Close'),
        }, {
            class: "btn btn-sm btn-secondary",
            onClick: () => this.model.mutex.exec(() => this.props.openDialog({ resId: record.id })),
            text: this.model.metaData.canEdit ? _t("Edit") : _t("View"),
        }];
    }
}
