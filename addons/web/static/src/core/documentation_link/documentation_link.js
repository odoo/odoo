import { Component, t, useProps, computed } from "@odoo/owl";

const LINK_REGEX = new RegExp("^https?://");

export class DocumentationLink extends Component {
    static template = "web.DocumentationLink";
    props = useProps({
        class: t.or([t.string(), t.object()]).optional(),
        path: t.string(),
        label: t.string().optional(),
        hideIcon: t.boolean().optional(false),
    });

    label = computed(() =>
        typeof this.props.label === "string" ? this.props.label : "View Documentation"
    );

    get url() {
        if (LINK_REGEX.test(this.props.path)) {
            return this.props.path;
        } else {
            return "/web/documentation" + this.props.path;
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
