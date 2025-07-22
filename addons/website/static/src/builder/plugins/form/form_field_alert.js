import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class FormFieldAlert extends Component {
    static template = "website.s_website_form_field_alert";
    static props = {
        message: String,
    };

    setup() {
        this.state = useState({
            message: undefined,
        });
        onWillStart(async () => this.handleProps(this.props));
        onWillUpdateProps(async (props) => this.handleProps(props));
    }
    async handleProps(props) {
        this.state.message = _t(props.message);
    }
}
