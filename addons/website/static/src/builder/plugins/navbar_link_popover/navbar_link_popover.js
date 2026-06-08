import { LinkPopover, linkPopoverProps } from "@html_editor/main/link/link_popover";
import { props, t } from "@odoo/owl";

export class NavbarLinkPopover extends LinkPopover {
    static template = "website.navbarLinkPopover";
    props = props({
        ...linkPopoverProps,
        onClickEditLink: t.function(),
        onClickEditMenu: t.function(),
    });

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
