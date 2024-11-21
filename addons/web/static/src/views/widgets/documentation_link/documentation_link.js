import { session } from "@web/session";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

const LINK_REGEX = new RegExp("^https?://");

export class DocumentationLink extends Component {
    static template = "web.DocumentationLink";
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: 1 }, // The record is not needed in this widget
        path: { type: String },
        label: { type: String, optional: 1 },
        icon: { type: String, optional: 1 },
        alertLink: { type: Boolean, optional: 1 },
    };

    get url() {
        if (LINK_REGEX.test(this.props.path)) {
            return this.props.path;
        } else {
            const serverVersion = session.server_version_info.includes("final")
                ? `${session.server_version_info[0]}.${session.server_version_info[1]}`.replace(
                      "~",
                      "-"
                  )
                : "master";
            return "https://www.odoo.com/documentation/" + serverVersion + this.props.path;
        }
    }

    get classes() {
        let classes = "o_doc_link me-2";
        if (this.props.alertLink){
            classes += " alert-link";
        }
        return classes;
    }
}

export const documentationLink = {
    component: DocumentationLink,
    extractProps: ({ attrs }) => {
        const { path, label, icon, alert_link } = attrs;
        return {
            path,
            label,
            icon,
            alertLink: Boolean(alert_link),
        };
    },
    additionalClasses: ["d-inline"],
};

registry.category("view_widgets").add("documentation_link", documentationLink);
