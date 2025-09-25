import { Component, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";

export class PortalProfileDialog extends Component {
    static template = "portal.PortalProfileDialog";
    static components = {
        Dialog,
        FileUploader,
    };
    static props = {
        close: Function,
        confirm: { type: Function, optional: true },
        userId: { type: Number },
    };
    static defaultProps = {
        confirm: () => {},
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.profileImg = useRef("profileImg");
        this.profileImgData = null;
        this.state = useState({
            isProcessing: false,
        });
    }

    get title() {
        return _t("Edit Profile");
    }

    onClearProfileImg() {
        this.profileImgData = false;
        this.profileImg.el.src = "/web/static/img/placeholder.png";
    }

    async onConfirm() {
        this.state.isProcessing = true;
        const data = {
            user_id: this.props.userId,
        };
        if (this.profileImgData != null) {
            data.image_1920 = this.profileImgData;
        }
        try {
            await rpc("/my/profile/user/save", data);
            if (this.props.confirm) {
                await this.props.confirm();
            }
            this.props.close();
        } catch {
            this.notification.add(_t("An error occurred while saving your profile."), {
                type: "danger",
            });
            this.state.isProcessing = false;
        }
    }

    onUploadProfileImg(file) {
        this.profileImg.el.src = `data:${file.type};base64,${file.data}`;
        this.profileImgData = file.data;
    }
}
