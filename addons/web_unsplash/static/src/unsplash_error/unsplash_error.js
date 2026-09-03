import { Component, t, useProps } from "@odoo/owl";
import { UnsplashCredentials } from "../unsplash_credentials/unsplash_credentials";

export class UnsplashError extends Component {
    static template = "web_unsplash.UnsplashError";
    static components = {
        UnsplashCredentials,
    };
    props = useProps({
        title: t.string(),
        subtitle: t.string(),
        showCredentials: t.boolean(),
        submitCredentials: t.function().optional(),
        hasCredentialsError: t.boolean().optional(),
    });
}
