import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WebsiteSaleShowEmptyOptionPlugin extends Plugin {
  static id = "showEmptyOption";
  resources = {
    builder_options: [
      withSequence(100, {
        template: "website_sale.ShowEmptyOption",
        selector: "#wrapwrap > header",
        editableOnly: false,
        groups: ["website.group_website_designer"],
      }),
    ],
  };
}

registry
  .category("website-plugins")
  .add(WebsiteSaleShowEmptyOptionPlugin.id, WebsiteSaleShowEmptyOptionPlugin);
