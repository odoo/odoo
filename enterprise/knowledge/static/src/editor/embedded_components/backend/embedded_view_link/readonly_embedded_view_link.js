import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { EMBEDDED_VIEW_LINK_STYLES } from "@knowledge/editor/embedded_components/core/embedded_view_link/embedded_view_link_style";
import { makeContext } from "@web/core/context";

export class ReadonlyViewLinkComponent extends Component {
    static template = "knowledge.ReadonlyEmbeddedViewLink";
    static props = {
        viewProps: { type: Object },
        linkStyle: { type: String, optional: true },
    };
    static defaultProps = {
        linkStyle: "link",
    };

    get displayName() {
        return this.props.viewProps.displayName;
    }

    get linkStyle() {
        return this.props.linkStyle;
    }

    setup() {
        this.actionService = useService("action");
    }

    getLinkClass() {
        return EMBEDDED_VIEW_LINK_STYLES[this.linkStyle].class;
    }

    async openViewLink() {
        const context = makeContext([this.props.viewProps.context || {}]);
        const action = await this.actionService.loadAction(
            this.props.viewProps.actWindow || this.props.viewProps.actionXmlId,
            context
        );
        if (action.type !== "ir.actions.act_window") {
            throw new Error(
                `Invalid action type "${action.type}". Expected "ir.actions.act_window"`
            );
        }
        if (this.displayName) {
            action.name = this.displayName;
            action.display_name = this.displayName;
        }
        action.globalState = {
            searchModel: this.props.viewProps.context.knowledge_search_model_state,
        };
        const props = {};
        if (action.context.orderBy) {
            try {
                props.orderBy = JSON.parse(this.action.context.orderBy);
            } catch {
                console.error("Parsing orderBy failed");
            }
        }
        this.actionService.doAction(action, {
            viewType: this.props.viewProps.viewType,
            props,
        });
    }
}

export const readonlyViewLinkEmbedding = {
    name: "viewLink",
    Component: ReadonlyViewLinkComponent,
    getProps: (host) => {
        return { ...getEmbeddedProps(host) };
    },
};
