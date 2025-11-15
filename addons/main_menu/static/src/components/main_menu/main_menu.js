import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WidgetHour } from "@main_menu/components/widget_hour/widget_hour";
import { WidgetAnnouncement } from "@main_menu/components/widget_announcement/widget_announcement";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

class MenuAction extends Component {
    static template = "main_menu.MainMenu";
    static components = { WidgetHour, WidgetAnnouncement };
    static props = {
        ...standardActionServiceProps
    };

    setup() {
        this.orm = useService("orm");
        this.menuService = useService("menu");
        this.company = user.activeCompany.id;

        this.apps = this.menuService.getApps()
                        .filter(app => app.xmlid != "main_menu.main_menu_root")
                        .sort((a, b) => a.name.localeCompare(b.name));

        onWillStart(async () => {
            try {
                const {showWidgets, announcement, userIsAdmin} = await rpc("/main_menu/announcement", {company_id: this.company});
                this.showWidgets = showWidgets;
                this.announcement = announcement;
                this.userIsAdmin = userIsAdmin;
            } catch (error){
                console.error("Error loading data:", error);
            }
        });
    }

    onClickModule(menu){
        menu && this.menuService.selectMenu(menu);
    }

    get cornerAngle() {
        const angle = 90 + 180 * Math.atan(window.innerHeight / window.innerWidth) / Math.PI;
        return `${angle}deg`;
    }
}

registry.category("actions").add("main_menu.action_open_main_menu", MenuAction);
