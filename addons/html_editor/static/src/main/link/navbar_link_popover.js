import { LinkPopover } from "./link_popover";

export class NavbarLinkPopover extends LinkPopover {
    static template = "html_editor.navbarLinkPopover";
    static props = {
        ...LinkPopover.props,
        onClickEditLink: Function,
        onClickEditMenu: Function,
    };

    /**
     * @override
     */
    onClickEdit() {
        const updateUrlAndLabel = this.updateUrlAndLabel.bind(this);
        const applyDeducedUrl = this.applyDeducedUrl.bind(this);
        const callback = () => {
            updateUrlAndLabel();
            applyDeducedUrl();
        };
        this.props.onClickEditLink(this, callback);
    }

    onClickEditMenu() {
        this.props.onClickEditMenu();
    }
}
