import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { HttpError403Option } from "./http_error_403_option";

class HttpError403OptionPlugin extends Plugin {
    static id = "HttpError403OptionPlugin";

    resources = {
        builder_options: [
            {
                OptionComponent: HttpError403Option,
                selector: ".s_403_error",
                title: _t("403 Error Message"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(HttpError403OptionPlugin.id, HttpError403OptionPlugin);
