import { Component } from "@odoo/owl";
import { PexelsCredentials } from "../pexels_credentials/pexels_credentials";

export class PexelsError extends Component {
    static template = "web_pexels.PexelsError";
    static components = {
        PexelsCredentials,
    };
    static props = {
        title: String,
        subtitle: String,
        showCredentials: Boolean,
        submitCredentials: { type: Function, optional: true },
        hasCredentialsError: { type: Boolean, optional: true },
    };
}
