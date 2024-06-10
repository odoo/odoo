/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class WebsiteEventTicketRegistrationDialog extends Component {
    static template = "website_event.WebsiteEventTicketRegistration";
    static components = { Dialog };
    static props = {
        close: Function,
        data: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.registrationCount = 0;
        this.registrations = useState(this.buildRegistrations());
        this.registrationsToDelete = useState([]);
    };

    get data() {
        return this.props.data;
    };

    buildRegistrations(){
        let registrations = [];
        if (this.props.data.registrations) {
            this.props.data.registrations.forEach(registration => {
                this.registrationCount++;
                registrations.push({
                    index: this.registrationCount,
                    registrationId: registration.registration_id,
                    ticketTypeId: registration.ticket_id,
                    ticketTypeName: registration.ticket_name,
                    answers: registration.answers,
                });
            });
        }
        else {
            this.props.data.tickets.forEach(ticketType => {
                for (let i = 1; i <= ticketType.quantity; i++) {
                    this.registrationCount++;
                    registrations.push({
                        index: this.registrationCount,
                        ticketTypeId: ticketType.id,
                        ticketTypeName: ticketType.name,
                        answers: Object.assign({}, ...this.props.data.event.specific_question_ids.map((question) => (
                            { [question.id]: (this.registrationCount === 1 && this.props.data.default_first_attendee !== undefined) ? this.props.data.default_first_attendee[question.question_type] : '' }
                        ))),
                    })
                }
            });
        }
        return registrations;
    }

    getAvailableTicketTypes(actualTicketTypeId) {
        return this.props.data.event.tickets_ids.filter((ticket) => ticket.seats_available > 0 && ticket.id !== actualTicketTypeId);
    };

    addRegistration() {
        this.registrationCount++;
        this.registrations.push({
            index: this.registrationCount,
            ticketTypeId: this.props.data.event.tickets_ids[0].id,
            ticketTypeName: this.props.data.event.tickets_ids[0].name,
            answers: [],
        });
    };

    removeRegistration(registrationIndex) {
        const index = this.registrations.findIndex((registration) => registration.index === registrationIndex);
        if ('registrationId' in this.registrations[index]) {
            this.registrationsToDelete.push(this.registrations[index].registrationId);
        }
        this.registrations.splice(index, 1);
    };

    changeTicketType(registrationIndex, ticketTypeId) {
        ticketTypeId = parseInt(ticketTypeId);
        let registation = this.registrations.find((registration) => registration.index === registrationIndex);
        registation.ticketTypeId = ticketTypeId;
        registation.ticketTypeName = this.props.data.event.tickets_ids.find((ticket) => ticket.id === ticketTypeId).name;
    };

    submitForm(event) {
        event.currentTarget.insertAdjacentHTML('afterbegin', '<i class="fa fa-circle-o-notch fa-spin me-1"></i>');
        event.currentTarget.disabled = true;
        const form = document.querySelector('form[id="attendee_registration"]');
        if (!form.checkValidity()) {
            form.requestSubmit();
            event.currentTarget.querySelector('i').remove();
            event.currentTarget.disabled = false;
        }
        else {
            form.requestSubmit();
        }
    }
};
