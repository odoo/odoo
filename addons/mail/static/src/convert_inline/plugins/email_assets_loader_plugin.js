import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";

/**
 * TODO EGGMAIL: these bundles do effectively nothing for the mail conversion,
 * they are added in python during `_prepare_mail_values`. This plugin is
 * here only for preview purposes. The style tag added in python is not
 * supported by every mail client, so relevant style should be set through
 * the style attribute
 */
export class EmailAssetsLoaderPlugin extends Plugin {
    static id = "EmailAssetsLoaderPlugin";
    resources = {
        email_conversion_bundle_names: ["mass_mailing.assets_email_html_conversion"],
        load_reference_content_handlers: this.loadAssets.bind(this),
    };

    loadAssets() {
        return this.getResource("email_conversion_bundle_names").map((bundle) =>
            loadBundle(bundle, {
                targetDoc: this.document,
                css: true,
                js: false,
            })
        );
    }
}

registry
    .category("mail-html-conversion-plugins")
    .add(EmailAssetsLoaderPlugin.id, EmailAssetsLoaderPlugin);
