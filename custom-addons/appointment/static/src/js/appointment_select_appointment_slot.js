/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
const { DateTime } = luxon;

publicWidget.registry.appointmentSlotSelect = publicWidget.Widget.extend({
    selector: '.o_appointment',
    events: {
        'change select[name="timezone"]': '_onRefresh',
        'change select[id="selectAppointmentResource"]': '_onRefresh',
        'change select[id="selectStaffUser"]': '_onRefresh',
        'change select[id="resourceCapacity"]': '_onRefresh',
        'click .o_js_calendar_navigate': '_onCalendarNavigate',
        'click .o_slot_button': '_onClickDaySlot',
        'click .o_slot_hours': '_onClickHoursSlot',
        'click button[name="submitSlotInfoSelected"]': '_onClickConfirmSlot',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * @override
     */
    start: function () {
        return this._super(...arguments).then(async () => {
            this.initSlots();
            this._removeLoadingSpinner();
            this.$first.click();
        });
    },

    /**
     * Initializes variables and design
     * - $slotsList: the block containing the availabilities
     * - $resourceSelection: the block containing the resources selection
     * - $first: the first day containing a slot
     */
    initSlots: async function () {
        this.$slotsList = this.$('#slotsList');
        this.$resourceSelection = this.$('#resourceSelection');
        this.$first = this.$('.o_slot_button').first();
        await this._updateSlotAvailability();
    },

    /**
     * Finds the first day with an available slot, replaces the currently shown month and
     * click on the first date where a slot is available.
     */
    selectFirstAvailableMonth: function () {
        const $firstMonth = this.$first.closest('.o_appointment_month');
        const $currentMonth = this.$('.o_appointment_month:not(.d-none)');
        $currentMonth.addClass('d-none');
        $currentMonth.find('table').removeClass('d-none');
        $currentMonth.find('.o_appointment_no_slot_month_helper').remove();
        $firstMonth.removeClass('d-none');
        this.$slotsList.empty();
        this.$first.click();
    },

    /**
     * Replaces the content of the calendar month with the no month helper.
     * Renders and appends its template to the element given as argument.
     * - $month: the month div to which we append the helper.
     */
     _renderNoAvailabilityForMonth: function ($month) {
        const firstAvailabilityDate = this.$first.attr('id');
        const staffUserName = this.$("#slots_form select[name='staff_user_id'] :selected").text();
        $month.find('table').addClass('d-none');
        $month.append(renderToElement('Appointment.appointment_info_no_slot_month', {
            firstAvailabilityDate: DateTime.fromISO(firstAvailabilityDate).toFormat("cccc dd MMMM yyyy"),
            staffUserName: staffUserName,
        }));
        $month.find('#next_available_slot').on('click', () => this.selectFirstAvailableMonth());
    },

    /**
     * Checks whether any slot is available in the calendar.
     * If there isn't, adds an explicative message in the slot list, and hides the appointment details,
     * and make design width adjustment to have the helper message centered to the whole width.
     * In case, there is no slots based on capacity chosen then the details and calendar are not hidden.
     * If the appointment is missconfigured (missing user or missing availabilities),
     * display an explicative message. The calendar is then not displayed.
     *
     */
     _updateSlotAvailability: function () {
        if (!this.$first.length) { // No slot available
            if (!this.$("select[name='resourceCapacity']").length) {
                this.$('#slots_availabilities').empty();
                this.$('.o_appointment_timezone_selection').addClass('d-none');
                const staffUserName = this.$("#slots_form select[name='staff_user_id'] :selected").text();
                const hideSelectDropdown = !!this.$("input[name='hide_select_dropdown']").val();
                const active = this.$("input[name='active']").val();
                this.$('.o_appointment_no_slot_overall_helper').empty().append(renderToElement('Appointment.appointment_info_no_slot', {
                    active: active,
                    appointmentsCount: this.$slotsList.data('appointmentsCount'),
                    staffUserName: hideSelectDropdown ? staffUserName : false,
                }));
            } else {
                this.$(".o_appointment_no_capacity").empty().append(renderToElement('Appointment.appointment_info_no_capacity'));
            }
        } else {
            this.$('.o_appointment_timezone_selection').removeClass('d-none');
            this.$(".o_appointment_no_capacity").empty();
        }
        if (this.$('.o_appointment_missing_configuration').hasClass('d-none')) {
            this.$('.o_appointment_missing_configuration').removeClass('d-none');
        }
    },

    /**
     * Navigate between the months available in the calendar displayed
     */
    _onCalendarNavigate: function (ev) {
        const parent = this.$('.o_appointment_month:not(.d-none)');
        let monthID = parseInt(parent.attr('id').split('-')[1]);
        monthID += ((this.$(ev.currentTarget).attr('id') === 'nextCal') ? 1 : -1);
        parent.find('table').removeClass('d-none');
        parent.find('.o_appointment_no_slot_month_helper').remove();
        parent.addClass('d-none');
        const $month = $(`div#month-${monthID}`).removeClass('d-none');
        this.$('.active').removeClass('active');
        this.$slotsList.empty();
        this.$resourceSelection.empty();

        if (!!this.$first.length) {
            // If there is at least one slot available, check if it is in the current month.
            if (!$month.find('.o_day').length) {
                this._renderNoAvailabilityForMonth($month);
            }
        }
    },

    /**
     * Display the list of slots available for the date selected
     */
    _onClickDaySlot: function (ev) {
        this.$('.o_slot_selected').removeClass('o_slot_selected active');
        this.$(ev.currentTarget).addClass('o_slot_selected active');

        // Do not display slots until user has actively selected the capacity
        if (this.$("select[name='resourceCapacity'] :selected").data('placeholderOption')) {
            return;
        }

        const slotDate = this.$(ev.currentTarget).data('slotDate');
        const slots = this.$(ev.currentTarget).data('availableSlots');
        const scheduleBasedOn = this.$("input[name='schedule_based_on']").val();
        const resourceAssignMethod = this.$("input[name='assign_method']").val();
        const resourceId = this.$("select[id='selectAppointmentResource']").val() || this.$("input[name='resource_selected_id']").val();
        const resourceCapacity = this.$("select[name='resourceCapacity']").val();
        let commonUrlParams = new URLSearchParams(window.location.search);
        // If for instance the chosen slot is already taken, then an error is thrown and the
        // user is brought back to the calendar view. In order to keep the selected user, the
        // url will contain the previously selected staff_user_id (-> preselected in the dropdown
        // if there is one). If one changes the staff_user in the dropdown, we do not want the
        // previous one to interfere, hence we delete it. The one linked to the slot is used.
        // The same is true for duration and date_time used in form rendering.
        commonUrlParams.delete('staff_user_id');
        commonUrlParams.delete('resource_selected_id');
        commonUrlParams.delete('duration');
        commonUrlParams.delete('date_time');
        if (resourceCapacity) {
            commonUrlParams.set('asked_capacity', encodeURIComponent(resourceCapacity));
        }
        if (resourceId) {
            commonUrlParams.set('resource_selected_id', encodeURIComponent(resourceId));
        }

        this.$slotsList.empty().append(renderToFragment('appointment.slots_list', {
            commonUrlParams: commonUrlParams,
            resourceAssignMethod: resourceAssignMethod,
            scheduleBasedOn: scheduleBasedOn,
            slotDate: DateTime.fromISO(slotDate).toFormat("cccc dd MMMM yyyy"),
            slots: slots,
            getAvailableResources: (slot) => {
                return scheduleBasedOn === 'resources' ? JSON.stringify(slot['available_resources']) : false;
            }
        }));
        this.$resourceSelection.addClass('d-none');
    },

    _onClickHoursSlot: function (ev) {
        this.$('.o_slot_hours.o_slot_hours_selected').removeClass('o_slot_hours_selected active');
        this.$(ev.currentTarget).addClass('o_slot_hours_selected active');

        // If not in 'time_resource' we directly go to the url for the slot
        // In the case we are in 'time_resource', we don't want to open the link as we want to select a resource
        // before confirming the slot.
        const assignMethod = this.$el.find("input[name='assign_method']").val();
        const scheduleBasedOn = this.$("input[name='schedule_based_on']").val();
        if (assignMethod !== "time_resource" || scheduleBasedOn === 'users') {
            const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
            const urlParameters = decodeURIComponent(this.$(".o_slot_hours_selected").data('urlParameters'));
            const url = new URL(
                `/appointment/${encodeURIComponent(appointmentTypeID)}/info?${urlParameters}`,
                location.origin);
            document.location = encodeURI(url.href);
            return;
        }

        const availableResources = this.$(ev.currentTarget).data('available_resources');
        const previousResourceIdSelected = this.$("select[name='resource_id']").val();
        this.$('#resourceSelection').empty().append(renderToFragment('appointment.resources_list', {
            availableResources: availableResources,
        }));
        this.$("select[name='resource_id']").attr('disabled', availableResources.length === 1);
        if (previousResourceIdSelected && this.$(`select[name='resource_id'] > option[value='${previousResourceIdSelected}']`).length) {
            this.$("select[name='resource_id']").val(previousResourceIdSelected);
        }
        this.$('#resourceSelection').removeClass('d-none');
    },

    _onClickConfirmSlot: function (ev) {
        const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
        const resourceId = parseInt(this.$("select[name='resource_id']").val());
        const resourceCapacity = parseInt(this.$("select[name='resourceCapacity']").val()) || 1;
        const urlParameters = decodeURIComponent(this.$(".o_slot_hours_selected").data('urlParameters'));
        const url = new URL(
            `/appointment/${encodeURIComponent(appointmentTypeID)}/info?${urlParameters}`,
            location.origin);
        const assignMethod = this.$("input[name='assign_method']").val();
        let resourceIds = JSON.parse(url.searchParams.get('available_resource_ids'));
        const $resourceSelected = $(this.$('.o_resources_list').prop('selectedOptions')[0]);
        if (assignMethod === "time_resource" && $resourceSelected.data('resourceCapacity') >= resourceCapacity) {
            resourceIds = [resourceId];
        }
        url.searchParams.set('resource_selected_id', encodeURIComponent(resourceId));
        url.searchParams.set('available_resource_ids', JSON.stringify(resourceIds));
        url.searchParams.set('asked_capacity', encodeURIComponent(resourceCapacity));
        document.location = encodeURI(url.href);
    },

    /**
     * Refresh the slots info when the user modifies the timezone or the selected user.
     */
    _onRefresh: async function (ev) {
        if (this.$("#slots_availabilities").length) {
            const daySlotSelected = this.$('.o_slot_selected').data('slotDate');
            const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
            const filterAppointmentTypeIds = this.$("input[name='filter_appointment_type_ids']").val();
            const filterUserIds = this.$("input[name='filter_staff_user_ids']").val();
            const inviteToken = this.$("input[name='invite_token']").val();
            const previousMonthName = this.$('.o_appointment_month:not(.d-none) .o_appointment_month_name').text();
            const staffUserID = this.$("#slots_form select[name='staff_user_id']").val();
            const resourceID = this.$("select[id='selectAppointmentResource']").val() || this.$("input[name='resource_selected_id']").val();
            const filterResourceIds = this.$("input[name='filter_resource_ids']").val();
            const timezone = this.$("select[name='timezone']").val();
            const resourceCapacity = this.$("select[name='resourceCapacity']").length && parseInt(this.$("select[name='resourceCapacity']").val()) || 1;
            this.$('.o_appointment_no_slot_overall_helper').empty();
            this.$slotsList.empty();
            this.$('#calendar, .o_appointment_timezone_selection').addClass('o_appointment_disable_calendar');
            this.$('#resourceSelection').empty();
            if (daySlotSelected && !this.$("select[name='resourceCapacity'] :selected").data('placeholderOption')) {
                this.$('.o_appointment_slot_list_loading').removeClass('d-none');
            }
            const updatedAppointmentCalendarHtml = await this.rpc(
                `/appointment/${appointmentTypeID}/update_available_slots`,
                {
                    asked_capacity: resourceCapacity,
                    invite_token: inviteToken,
                    filter_appointment_type_ids: filterAppointmentTypeIds,
                    filter_staff_user_ids: filterUserIds,
                    filter_resource_ids: filterResourceIds,
                    month_before_update: previousMonthName,
                    resource_selected_id: resourceID,
                    staff_user_id: staffUserID,
                    timezone: timezone,
                }
            );
            if (updatedAppointmentCalendarHtml) {
                this.$("#slots_availabilities").replaceWith(updatedAppointmentCalendarHtml);
                this.initSlots();
                // If possible, we keep the current month, and display the helper if it has no availability.
                const $displayedMonth = this.$('.o_appointment_month:not(.d-none)');
                if (!!this.$first.length && !$displayedMonth.find('.o_day').length) {
                    this._renderNoAvailabilityForMonth($displayedMonth);
                }
                this._removeLoadingSpinner();
                this.$(`div[data-slot-date="${daySlotSelected}"]`).click();
            }
        }
    },

    /**
     * Remove the loading spinners when no longer useful
     */
    _removeLoadingSpinner: function () {
        this.$('.o_appointment_slots_loading').remove();
        this.$('.o_appointment_slot_list_loading').addClass('d-none');
        this.$('#slots_availabilities').removeClass('d-none');
        this.$('#calendar, .o_appointment_timezone_selection').removeClass('o_appointment_disable_calendar');
    },
});
