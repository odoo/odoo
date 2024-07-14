/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { onMounted, onWillUnmount } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { EnterpriseNavBar } from "@web_enterprise/webclient/navbar/navbar";
import { HomeMenuCustomizer } from "./home_menu_customizer/home_menu_customizer";
import { useStudioServiceAsReactive, NotEditableActionError } from "@web_studio/studio_service";

const menuButtonsRegistry = registry.category("studio_navbar_menubuttons");
export class StudioNavbar extends EnterpriseNavBar {
    setup() {
        super.setup();
        this.studio = useStudioServiceAsReactive();
        this.actionManager = useService("action");
        this.user = useService("user");
        this.dialogManager = useService("dialog");
        this.notification = useService("notification");
        onMounted(() => {
            this.env.bus.removeEventListener("HOME-MENU:TOGGLED", this._busToggledCallback);
            this._updateMenuAppsIcon();
        });

        const onMenuButtonsUpdate = () => this.render();
        menuButtonsRegistry.addEventListener("UPDATE", onMenuButtonsUpdate);
        onWillUnmount(() => menuButtonsRegistry.removeEventListener("UPDATE", onMenuButtonsUpdate));
    }
    onMenuToggle() {
        this.studio.toggleHomeMenu();
    }
    closeStudio() {
        this.studio.leave();
    }
    async onNavBarDropdownItemSelection(menu) {
        if (menu.actionID) {
            try {
                await this.studio.open(this.studio.MODES.EDITOR, menu.actionID);
            } catch (e) {
                if (e instanceof NotEditableActionError) {
                    const options = { type: "danger" };
                    this.notification.add(_t("This action is not editable by Studio"), options);
                    return;
                }
                throw e;
            }
        }
    }
    get hasBackgroundAction() {
        return this.studio.editedAction || this.studio.MODES.APP_CREATOR === this.studio.mode;
    }
    get isInApp() {
        return this.studio.mode === this.studio.MODES.EDITOR;
    }
    get menuButtons() {
        return Object.fromEntries(menuButtonsRegistry.getEntries());
    }
}
StudioNavbar.template = "web_studio.StudioNavbar";
StudioNavbar.components.HomeMenuCustomizer = HomeMenuCustomizer;
