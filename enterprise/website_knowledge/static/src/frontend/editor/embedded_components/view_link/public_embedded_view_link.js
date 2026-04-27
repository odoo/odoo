import { Component } from "@odoo/owl";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { EMBEDDED_VIEW_LINK_STYLES } from "@knowledge/editor/embedded_components/core/embedded_view_link/embedded_view_link_style";

export class PublicEmbeddedViewLinkComponent extends Component {
    static template = "knowledge.PublicEmbeddedViewLink";
    static props = {
        viewProps: { type: Object },
        linkStyle: { type: String, optional: true },
    };
    static defaultProps = {
        linkStyle: "link",
    };

    getLinkClass() {
        return EMBEDDED_VIEW_LINK_STYLES[this.props.linkStyle].class;
    }
}

export const publicViewLinkEmbedding = {
    name: "viewLink",
    Component: PublicEmbeddedViewLinkComponent,
    getProps: (host) => {
        return { ...getEmbeddedProps(host) };
    },
};
