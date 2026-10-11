import { registry } from "@web/core/registry";
import { UrlField, urlField } from "../url/url_field";

class DocumentationLinkField extends UrlField {
    isReadonly() {
        return true;
    }

    get formattedHref() {
        const href = super.formattedHref;
        const matches = href.match(/^https:\/\/www\.odoo\.com\/documentation\/latest(.*)$/);
        return matches ? "/web/documentation" + matches[1] : href;
    }
}

export const documentationLinkField = {
    ...urlField,
    component: DocumentationLinkField,
};

registry.category("fields").add("documentation_link", documentationLinkField);
