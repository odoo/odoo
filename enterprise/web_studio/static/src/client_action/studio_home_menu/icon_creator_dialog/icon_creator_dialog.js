import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { IconCreator } from "@web_studio/client_action/icon_creator/icon_creator";

import { Component, useState } from "@odoo/owl";

export class IconCreatorDialog extends Component {
    static props = {
        editedAppData: Object,
        appId: Number,
        close: Function,
    };
    static template = "web_studio.IconCreatorDialog";
    static components = { Dialog, IconCreator };

    setup() {
        this.menus = useService("menu");
        this.initialAppData = { ...this.props.editedAppData };
        this.editedAppData = useState(this.props.editedAppData);
    }

    /**
     * @param {Object} icon
     */
    onIconChanged(icon) {
        for (const key in this.editedAppData) {
            delete this.editedAppData[key];
        }
        for (const key in icon) {
            this.editedAppData[key] = icon[key];
        }
    }

    async saveIcon() {
        const { type } = this.initialAppData;
        const appId = this.props.appId;
        let iconValue;
        if (this.editedAppData.type !== type) {
            // different type
            if (this.editedAppData.type === "base64") {
                iconValue = this.editedAppData.uploaded_attachment_id;
            } else {
                const { iconClass, color, backgroundColor } = this.editedAppData;
                iconValue = [iconClass, color, backgroundColor];
            }
        } else if (this.editedAppData.type === "custom_icon") {
            // custom icon changed
            const { iconClass, color, backgroundColor } = this.editedAppData;
            if (
                this.initialAppData.iconClass !== iconClass ||
                this.initialAppData.color !== color ||
                this.initialAppData.backgroundColor !== backgroundColor
            ) {
                iconValue = [iconClass, color, backgroundColor];
            }
        } else if (this.editedAppData.uploaded_attachment_id) {
            // new attachment
            iconValue = this.editedAppData.uploaded_attachment_id;
        }

        if (iconValue) {
            await rpc("/web_studio/edit_menu_icon", {
                context: user.context,
                icon: iconValue,
                menu_id: appId,
            });
            await this.menus.reload();
        }
        this.props.close();
    }
}
