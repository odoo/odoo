import { Component, useState } from "@odoo/owl";

export class PexelsCredentials extends Component {
    static template = "web_pexels.PexelsCredentials";
    static props = {
        submitCredentials: Function,
        hasCredentialsError: Boolean,
    };
    setup() {
        this.state = useState({
            key: "",
            hasKeyError: this.props.hasCredentialsError,
        });
    }

    submitCredentials() {
        if (this.state.key === "") {
            this.state.hasKeyError = true;
        } else {
            this.props.submitCredentials(this.state.key);
        }
    }
}
