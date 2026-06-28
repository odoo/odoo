import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { documentationUrl } from "@web/core/utils/urls";

const LINK_REGEX = new RegExp("^https?://");

export class DocumentationLink extends Component {
    static template = "web.DocumentationLink";
    props = props({
        ...standardWidgetProps,
        class: t.or([t.string(), t.object()]).optional("me-2"),
        record: t.object().optional(), // The record is not needed in this widget
        path: t.string(),
        label: t.string().optional(),
        icon: t.string().optional(),
    });

    get url() {
        if (LINK_REGEX.test(this.props.path)) {
            return this.props.path;
        } else {
            return documentationUrl(this.props.path);
        }
    }

    get classes() {
        let classes = "o_doc_link";
        if (this.props.class) {
            if (this.props.class instanceof Object) {
                classes = { ...this.props.class, [classes]: true };
            } else {
                classes += " " + this.props.class;
            }
        }
        return classes;
    }
}

export const documentationLink = {
    component: DocumentationLink,
    extractProps: ({ attrs }) => {
        const { path, label, icon, class: classes } = attrs;
        return {
            path,
            label,
            icon,
            class: classes,
        };
    },
    additionalClasses: ["d-inline"],
};

registry.category("view_widgets").add("documentation_link", documentationLink);
