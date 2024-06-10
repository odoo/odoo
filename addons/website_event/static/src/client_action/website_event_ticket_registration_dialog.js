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
        this.isEventFull = useState({ value: false });
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
                this.updateTicketSeatsAvailability({ticketId: registration.ticket_id, qtyRemoved: 1});
            });
            this.updateEventSeatsAvailability({qtyRemoved: this.props.data.registrations.length});
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
                this.updateTicketSeatsAvailability({ticketId: ticketType.id, qtyRemoved: ticketType.quantity});
                this.updateEventSeatsAvailability({qtyRemoved: ticketType.quantity});
            });
        }
        return registrations;
    }

    getAvailableTicketTypes(actualTicketTypeId) {
        return this.props.data.event.tickets_ids.filter((ticket) => ticket.id !== actualTicketTypeId);
    };

    updateTicketSeatsAvailability({ticketId, qtyAdded = 0, qtyRemoved = 0}) {
        if (this.props.data.event.tickets_ids.length === 0) return;
        const ticketIndex = this.props.data.event.tickets_ids.findIndex((ticket) => ticket.id === ticketId);
        if (this.props.data.event.tickets_ids[ticketIndex].seats_available !== null){
            this.props.data.event.tickets_ids[ticketIndex].seats_available += qtyAdded - qtyRemoved;
        }
    };

    updateEventSeatsAvailability({qtyAdded = 0, qtyRemoved = 0}) {
        if (this.data.event.seats_limited) {
            this.data.event.seats_available += qtyAdded - qtyRemoved;
            if (this.data.event.seats_available === 0) {
                this.isEventFull.value = true;
            } else if (this.data.event.seats_available > 0) {
                this.isEventFull.value = false;
            }
        }
    };

    addRegistration() {
        this.registrationCount++;
        let ticketType;
        if (this.props.data.event.tickets_ids.length === 0) {
            ticketType = {
                id: this.props.data.tickets[0].id,
                name: this.props.data.tickets[0].name,
            }
        } else {
            const lastRegistrationTicketType = this.props.data.event.tickets_ids.find((ticket) =>
                ticket.id === this.registrations[this.registrations.length - 1].ticketTypeId
            );
            if (lastRegistrationTicketType.seats_available > 0) {
                ticketType = lastRegistrationTicketType;
            } else {
                ticketType = this.props.data.event.tickets_ids.find((ticket) => ticket.seats_available > 0);
            }
        }
        this.updateEventSeatsAvailability({qtyRemoved: 1});
        this.updateTicketSeatsAvailability({ticketId: ticketType.id, qtyRemoved: 1});
        this.registrations.push({
            index: this.registrationCount,
            ticketTypeId: ticketType.id,
            ticketTypeName: ticketType.name,
            answers: [],
        });
    };

    removeRegistration(registrationIndex) {
        const index = this.registrations.findIndex((registration) => registration.index === registrationIndex);
        this.updateEventSeatsAvailability({qtyAdded: 1});
        this.updateTicketSeatsAvailability({ticketId: this.registrations[index].ticketTypeId, qtyAdded: 1});
        if ('registrationId' in this.registrations[index]) {
            this.registrationsToDelete.push(this.registrations[index].registrationId);
        }
        this.registrations.splice(index, 1);
    };

    changeTicketType(registrationIndex, ticketTypeId) {
        ticketTypeId = parseInt(ticketTypeId);
        let registation = this.registrations.find((registration) => registration.index === registrationIndex);
        this.updateTicketSeatsAvailability({ticketId: registation.ticketTypeId, qtyAdded: 1});
        this.updateTicketSeatsAvailability({ticketId: ticketTypeId, qtyRemoved: 1});
        registation.ticketTypeId = ticketTypeId;
        registation.ticketTypeName = this.props.data.event.tickets_ids.find((ticket) => ticket.id === ticketTypeId).name;
    };

    submitForm(ev) {
        ev.currentTarget.insertAdjacentHTML('afterbegin', '<i class="fa fa-circle-o-notch fa-spin me-1"></i>');
        ev.currentTarget.disabled = true;
        const form = document.querySelector('form[id="attendee_registration"]');
        if (!form.checkValidity()) {
            form.requestSubmit();
            ev.currentTarget.querySelector('i').remove();
            ev.currentTarget.disabled = false;
        }
        else {
            form.requestSubmit();
        }
    }
};
