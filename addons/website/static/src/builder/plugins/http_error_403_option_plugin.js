import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class HttpError403Option extends BaseOptionComponent {
    static template = "website.HttpError403Option";
    static selector = ".s_403_error";
    static title = _t("403 Error Message");
    static editableOnly = false;
}
/**
 * This plugin adds a builder option to the website editor to allow
 * users to configure a 403 Forbidden error message.
 */
class HttpError403OptionPlugin extends Plugin {
    static id = "httpError403Option";

    resources = {
        builder_options: [HttpError403Option],
    };
}

registry.category("website-plugins").add(HttpError403OptionPlugin.id, HttpError403OptionPlugin);
