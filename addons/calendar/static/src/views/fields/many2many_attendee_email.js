import { 
    Many2ManyAttendee,
    many2ManyAttendee,
} from "./many2many_attendee";
import { FieldMany2ManyTagsEmailMany2xAutocomplete } from "@mail/views/web/fields/many2many_tags_email/many2many_tags_email";
import { registry } from "@web/core/registry";


export class Many2ManyAttendeeEmail extends Many2ManyAttendee {
    static template = "calendar.Many2ManyAttendeeEmail";
    static components = {
        ...super.components,
        Many2XAutocomplete: FieldMany2ManyTagsEmailMany2xAutocomplete,
    };
}

export const many2ManyAttendeeEmail = {
    ...many2ManyAttendee,
    component: Many2ManyAttendeeEmail,
};

registry.category("fields").add("many2manyattendee_email", many2ManyAttendeeEmail);
