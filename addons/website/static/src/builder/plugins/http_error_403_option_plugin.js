import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/**
 * HttpError403OptionPlugin
 *
 * This plugin adds a builder option to the website editor to allow
 * the user to configure a 403 Forbidden error message display.
 */
class HttpError403OptionPlugin extends Plugin {
    static id = "HttpError403OptionPlugin";

    resources = {
        builder_options: [
            {
                template: "website.HttpError403Option",
                selector: ".s_403_error",
                title: _t("403 Error Message"),
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(HttpError403OptionPlugin.id, HttpError403OptionPlugin);
