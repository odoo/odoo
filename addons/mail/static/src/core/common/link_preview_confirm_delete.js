import { useSubEnv } from "@web/owl2/utils";
import { Component, props, types } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class LinkPreviewConfirmDelete extends Component {
    static components = { Dialog };
    static template = "mail.LinkPreviewConfirmDelete";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            close: types.function([]),
            LinkPreview: types.component(), // cannot import LinkPreview due to circular dependency
            messageLinkPreview: types.instanceOf(this.store["mail.message.link.preview"].Class),
        });
        useSubEnv({ inLinkPreviewConfirmDelete: true });
    }

    onClickOk() {
        this.props.messageLinkPreview.hide();
        this.props.close();
    }

    onClickDeleteAll() {
        this.props.messageLinkPreview.message_id.hideAllLinkPreviews();
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
