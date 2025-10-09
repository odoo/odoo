import { FormRenderer } from "@web/views/form/form_renderer";

import { HRChatter } from "@hr/components/mail/chatter";

export class EmployeeFormRenderer extends FormRenderer {
    setup() {
        super.setup()
        this.mailComponents.Chatter = HRChatter;
    }
}
