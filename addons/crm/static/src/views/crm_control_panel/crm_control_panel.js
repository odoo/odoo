import { ControlPanel } from "@web/search/control_panel/control_panel";
import { TeamSwitcher } from "@crm/components/team_switcher/team_switcher";

export class CrmControlPanel extends ControlPanel {
    static template = "crm.ControlPanel";
    static components = {
        ...ControlPanel.components,
        TeamSwitcher,
    };
};
