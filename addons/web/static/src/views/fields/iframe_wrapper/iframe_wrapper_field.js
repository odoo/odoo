import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { Component, useEffect, useRef } from "@odoo/owl";

export class IframeWrapperField extends Component {
    static template = "web.IframeWrapperField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.iframeRef = useRef("iframe");

        useEffect(
            (value) => {
                /**
                 * The document.write is not recommended. It is better to manipulate the DOM through $.appendChild and
                 * others. In our case though, we deal with an iframe without src attribute and with metadata to put in
                 * head tag. If we use the usual dom methods, the iframe is automatically created with its document
                 * component containing html > head & body. Therefore, if we want to make it work that way, we would
                 * need to receive each piece at a time to  append it to this document (with this.record.data and extra
                 * model fields or with an rpc). It also cause other difficulties getting attribute on the most parent
                 * nodes, parsing to HTML complex elements, etc.
                 * Therefore, document.write makes it much more trivial in our situation.
                 */
                const iframeDoc = this.iframeRef.el.contentDocument;
                iframeDoc.open();
                iframeDoc.write(value);
                iframeDoc.close();
            },
            () => [this.props.record.data[this.props.name]]
        );
    }
}

export const iframeWrapperField = {
    component: IframeWrapperField,
    displayName: _t("Wrap raw html within an iframe"),
    // If HTML, don't forget to adjust the sanitize options to avoid stripping most of the metadata
    supportedTypes: ["text", "html"],
};

registry.category("fields").add("iframe_wrapper", iframeWrapperField);
