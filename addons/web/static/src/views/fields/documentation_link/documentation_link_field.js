import { registry } from "@web/core/registry";
import { documentationUrl } from "@web/core/utils/urls";
import { UrlField, urlField } from "../url/url_field";

class DocumentationLinkField extends UrlField {
    get isReadonly() {
        return true;
    }

    get readonlyText() {
        return this.props.text || this.formattedHref;
    }

    get formattedHref() {
        const href = super.formattedHref;
        const matches = href.match(/odoo\.com\/documentation\/latest(.*)$/);
        return matches ? documentationUrl(matches[1]) : href;
    }
}

export const documentationLinkField = {
    ...urlField,
    component: DocumentationLinkField,
};

registry.category("fields").add("documentation_link", documentationLinkField);
