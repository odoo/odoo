/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { useService } from "@web/core/utils/hooks";
import { NotEditableActionError } from "../../studio_service";
import { IconCreatorDialog } from "./icon_creator_dialog/icon_creator_dialog";

import { onMounted, onWillUnmount, useRef } from "@odoo/owl";
const NEW_APP_BUTTON = {
    isNewAppButton: true,
    label: _t("New App"),
    webIconData: "/web_studio/static/src/img/default_icon_app.png",
};

/**
 * Studio home menu
 *
 * Studio version of the standard enterprise home menu. It has roughly the same
 * implementation, with the exception of the app icon edition and the app creator.
 * @extends HomeMenu
 */
export class StudioHomeMenu extends HomeMenu {
    /**
     * @param {Object} props
     * @param {Object[]} props.apps application icons
     * @param {string} props.apps[].action
     * @param {number} props.apps[].id
     * @param {string} props.apps[].label
     * @param {string} props.apps[].parents
     * @param {(boolean|string|Object)} props.apps[].webIcon either:
     *      - boolean: false (no webIcon)
     *      - string: path to Odoo icon file
     *      - Object: customized icon (background, class and color)
     * @param {string} [props.apps[].webIconData]
     * @param {string} props.apps[].xmlid
     */
    setup() {
        super.setup(...arguments);

        this.user = useService("user");
        this.studio = useService("studio");
        this.notifications = useService("notification");
        this.dialog = useService("dialog");
        this.root = useRef("root");

        onMounted(() => {
            this.canEditIcons = true;
            document.body.classList.add("o_home_menu_background");
            document.body.classList.toggle(
                "o_home_menu_background_custom",
                this.menus.getMenu("root").backgroundImage
            );
        });

        onWillUnmount(() => {
            document.body.classList.remove(
                "o_home_menu_background",
                "o_home_menu_background_custom"
            );
        });
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    get displayedApps() {
        return [...super.displayedApps, NEW_APP_BUTTON];
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    async _openMenu(menu) {
        if (menu.isNewAppButton) {
            this.canEditIcons = false;
            return this.studio.open(this.studio.MODES.APP_CREATOR);
        } else {
            try {
                await this.studio.open(this.studio.MODES.EDITOR, menu.actionID);
                this.menus.setCurrentMenu(menu);
            } catch (e) {
                if (e instanceof NotEditableActionError) {
                    const options = { type: "danger" };
                    this.notifications.add(_t("This action is not editable by Studio"), options);
                    return;
                }
                throw e;
            }
        }
    }

    _enableAppsSorting() {
        return false;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {Object} app
     */
    onEditIconClick(app) {
        if (!this.canEditIcons) {
            return;
        }
        const editedAppData = {};
        if (app.webIconData) {
            Object.assign(editedAppData, {
                webIconData: app.webIconData,
                type: "base64",
            });
        } else {
            Object.assign(editedAppData, {
                backgroundColor: app.webIcon.backgroundColor,
                color: app.webIcon.color,
                iconClass: app.webIcon.iconClass,
                type: "custom_icon",
            });
        }

        const dialogProps = {
            editedAppData,
            appId: app.id,
        };
        this.dialog.add(IconCreatorDialog, dialogProps);
    }
}

StudioHomeMenu.props = { apps: HomeMenu.props.apps };
StudioHomeMenu.template = "web_studio.StudioHomeMenu";
