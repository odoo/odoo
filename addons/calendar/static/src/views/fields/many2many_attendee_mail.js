import { 
    Many2ManyAttendee,
    many2ManyAttendee,
} from "./many2many_attendee";
import { Many2XAvatarUserAutocomplete } from "@mail/views/web/fields/avatar_autocomplete/avatar_many2x_autocomplete";
import { makeContext } from "@web/core/context";
import { registry } from "@web/core/registry";


export class Many2XAvatarMailUserAutocomplete extends Many2XAvatarUserAutocomplete {
    static defaultProps = {
        ...super.defaultProps,
        emailCreateField: "email",
    };
    getCreationContext(value) {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (pattern.test(value)) {
            return makeContext([
                this.props.context,
                value && { [`default_${this.props.emailCreateField}`]: value },
                value && { [`default_${this.props.nameCreateField}`]: value },
            ]);
        } else {
            return makeContext([
                this.props.context,
                value && { [`default_${this.props.nameCreateField}`]: value },
            ]);
        }
    }
}

export class Many2ManyAttendeeMail extends Many2ManyAttendee {
    static components = {
        ...super.components,
        Many2XAutocomplete: Many2XAvatarMailUserAutocomplete,
    };
}

export const many2ManyAttendeeMail = {
    ...many2ManyAttendee,
    component: Many2ManyAttendeeMail,
};

registry.category("fields").add("many2manyattendee_mail", many2ManyAttendeeMail);