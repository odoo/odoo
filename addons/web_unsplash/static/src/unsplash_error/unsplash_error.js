import { Component } from "@odoo/owl";
import { UnsplashCredentials } from "../unsplash_credentials/unsplash_credentials";

export class UnsplashError extends Component {
    static template = "web_unsplash.UnsplashError";
    static components = {
        UnsplashCredentials,
    };
    static props = {
        title: String,
        subtitle: String,
        showCredentials: Boolean,
        submitCredentials: { type: Function, optional: true },
        hasCredentialsError: { type: Boolean, optional: true },
    };
}
