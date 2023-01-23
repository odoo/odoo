/** @odoo-module **/

import { session } from "@web/session";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

const LINK_REGEX = new RegExp("^https?://");

export class DocumentationLink extends Component {
    get url() {
        if (LINK_REGEX.test(this.props.path)) {
            return this.props.path;
        } else {
            const serverVersion = session.server_version.includes("alpha")
                ? "master"
                : session.server_version;
            return "https://www.odoo.com/documentation/" + serverVersion + this.props.path;
        }
    }
}
DocumentationLink.template = "web.DocumentationLink";
DocumentationLink.props = {
    ...standardWidgetProps,
    record: { type: Object, optional: 1 }, // The record is not needed in this widget
    path: { type: String },
};
DocumentationLink.extractProps = ({ attrs }) => {
    const { path } = attrs;
    return {
        path,
    };
};
DocumentationLink.additionalClasses = ["d-inline"];

registry.category("view_widgets").add("documentation_link", DocumentationLink);
