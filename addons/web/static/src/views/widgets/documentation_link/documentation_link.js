import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { documentationUrl } from "@web/core/utils/urls";

const LINK_REGEX = new RegExp("^https?://");

export class DocumentationLink extends Component {
    static template = "web.DocumentationLink";
    props = useProps({
        ...standardWidgetProps,
        class: t.or([t.string(), t.object()]).optional("me-2"),
        record: t.object().optional(), // The record is not needed in this widget
        path: t.string(),
        label: t.string().optional(),
        icon: t.string().optional(),
        iconPosition: t.selection(["left", "right"]).optional("left"),
        iconClass: t.or([t.string(), t.object()]).optional(),
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
        if (this.props.iconPosition === "right") {
            classes += " d-inline-flex flex-row-reverse align-items-center";
        }
        if (this.props.class) {
            if (this.props.class instanceof Object) {
                classes = {
                    ...this.props.class,
                    ...classes.split(" ").reduce((acc, cur) => ((acc[cur] = true), acc), {}),
                };
            } else {
                classes += " " + this.props.class;
            }
        }
        return classes;
    }

    get iconClasses() {
        let classes = "oi " + (this.props.iconPosition === "left" ? "pe-1" : "ps-1");
        if (this.props.iconClass) {
            if (this.props.iconClass instanceof Object) {
                classes = {
                    ...this.props.iconClass,
                    ...classes.split(" ").reduce((acc, cur) => ((acc[cur] = true), acc), {}),
                };
            } else {
                classes += " " + this.props.iconClass;
            }
        }
        return classes;
    }
}

export const documentationLink = {
    component: DocumentationLink,
    extractProps: ({ attrs }) => {
        const {
            path,
            label,
            icon,
            class: classes,
            "icon-position": iconPosition,
            "icon-class": iconClass,
        } = attrs;
        return {
            path,
            label,
            icon,
            iconPosition,
            iconClass,
            class: classes,
        };
    },
    additionalClasses: ["d-inline"],
};

registry.category("view_widgets").add("documentation_link", documentationLink);
