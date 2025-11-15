import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class WidgetAnnouncement extends Component {
    static template = "main_menu.WidgetAnnouncement";
    static props = {
        userIsAdmin: Boolean,
        announcement: String,
    };

    setup(){
        this.notification = useService("notification");
        this.company = user.activeCompany.id;
        this.state = useState({
            announcement: this.props.announcement,
        });
    }

    onInputAnnouncement(e) {
        this.state.announcement = e.target.value;
    }

    async onSaveAnnouncement(){
        try {
            await rpc("/main_menu/announcement/save", {
                company_id: this.company,
                data: { announcement: this.state.announcement }
            });
            this.notification.add(_t("Announcement saved."), { type: "success" });
        } catch (error){
            console.error("Error saving data:", error);
            this.notification.add(_t("The announcement could not be saved. Please try again."), { type: "danger" });
        }
    }
}
