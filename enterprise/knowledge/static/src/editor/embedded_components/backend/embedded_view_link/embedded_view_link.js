import {
    getEmbeddedProps,
    useEmbeddedState,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { EmbeddedViewLinkPopover } from "@knowledge/editor/embedded_components/backend/embedded_view_link/embedded_view_link_popover";
import { EmbeddedViewLinkEditDialog } from "@knowledge/editor/embedded_components/backend/embedded_view_link/embedded_view_link_edit_dialog";
import { ReadonlyViewLinkComponent } from "@knowledge/editor/embedded_components/backend/embedded_view_link/readonly_embedded_view_link";

export class EmbeddedViewLinkComponent extends ReadonlyViewLinkComponent {
    static template = "knowledge.EmbeddedViewLink";
    static props = {
        ...ReadonlyViewLinkComponent.props,
        host: { type: Object },
        copyViewLink: { type: Function },
        removeViewLink: { type: Function },
    };

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.popover = usePopover(EmbeddedViewLinkPopover, {
            popoverClass: "o_edit_menu_popover",
        });
        this.embeddedState = useEmbeddedState(this.props.host);
    }

    set displayName(value) {
        this.embeddedState.displayName = value;
    }

    get displayName() {
        return this.embeddedState.displayName;
    }

    set linkStyle(value) {
        this.embeddedState.linkStyle = value;
    }

    get linkStyle() {
        return this.embeddedState.linkStyle;
    }

    onCopyViewLinkClick() {
        this.props.copyViewLink();
        this.popover.close();
    }

    onEditViewLinkClick() {
        this.dialogService.add(EmbeddedViewLinkEditDialog, {
            name: this.displayName || "",
            style: this.linkStyle,
            onSave: (name, style) => {
                this.displayName = name;
                this.linkStyle = style;
            },
        });
        this.popover.close();
    }

    onRemoveViewLinkClick() {
        this.props.removeViewLink(this.displayName || "");
        this.popover.close();
    }

    openEmbeddedViewLinkPopover() {
        this.popover.open(this.props.host, {
            name: this.displayName,
            openViewLink: this.openViewLink.bind(this),
            onCopyViewLinkClick: this.onCopyViewLinkClick.bind(this),
            onEditViewLinkClick: this.onEditViewLinkClick.bind(this),
            onRemoveViewLinkClick: this.onRemoveViewLinkClick.bind(this),
        });
    }
}

export const viewLinkEmbedding = {
    name: "viewLink",
    Component: EmbeddedViewLinkComponent,
    getProps: (host) => {
        return { host, ...getEmbeddedProps(host) };
    },
    getStateChangeManager: (config) => {
        return new StateChangeManager(
            Object.assign(config, {
                getEmbeddedState: (host) => {
                    const props = getEmbeddedProps(host);
                    return {
                        displayName: props.viewProps.displayName,
                        linkStyle: props.linkStyle || "link",
                    };
                },
                stateToEmbeddedProps: (host, state) => {
                    const props = getEmbeddedProps(host);
                    props.viewProps.displayName = state.displayName;
                    props.linkStyle = state.linkStyle;
                    return props;
                },
            })
        );
    },
};
