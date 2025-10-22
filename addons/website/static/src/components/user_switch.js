import { UserSwitch } from "@web/core/user_switch/user_switch";
import { registry } from "@web/core/registry";
export class UserSwitchEdit extends UserSwitch {
    static template = "website.login_user_switch.edit";
}

registry.category("public_components.edit").add("web.user_switch", UserSwitchEdit);
