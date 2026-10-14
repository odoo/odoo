import { Component, proxy, t, useProps } from "@odoo/owl";
import { DocumentationLink } from "@web/core/documentation_link/documentation_link";

export class UnsplashCredentials extends Component {
    static template = "web_unsplash.UnsplashCredentials";
    static components = { DocumentationLink };
    props = useProps({
        submitCredentials: t.function(),
        hasCredentialsError: t.boolean(),
    });
    setup() {
        this.state = proxy({
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
