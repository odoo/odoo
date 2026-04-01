import { Component, useState } from "@odoo/owl";

export class UnsplashCredentials extends Component {
    static template = "web_unsplash.UnsplashCredentials";
    static props = {
        submitCredentials: Function,
        hasCredentialsError: Boolean,
    };
    setup() {
        this.state = useState({
            key: "",
            appId: "",
            hasKeyError: this.props.hasCredentialsError,
            hasAppIdError: this.props.hasCredentialsError,
        });
    }

    submitCredentials() {
        if (this.state.key === "") {
            this.state.hasKeyError = true;
        } else if (this.state.appId === "") {
            this.state.hasAppIdError = true;
        } else {
            this.props.submitCredentials(this.state.key, this.state.appId);
        }
    }
}
