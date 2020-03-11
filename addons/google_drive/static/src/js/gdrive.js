odoo.define('google_drive.ActionMenus', function (require) {
    "use strict";

    const ActionMenus = require('web.ActionMenus');
    const DropdownMenuItem = require('web.DropdownMenuItem');

    /**
     * Google drive menu
     *
     * This component is actually a set of list items used to enrich the ActionMenus's
     * "Action" dropdown list (@see ActionMenus). It will fetch
     * the current user's google drive configuration and set the result as its
     * items if any.
     * @extends DropdownMenuItem
     */
    class GoogleDriveMenu extends DropdownMenuItem {

        async willStart() {
            if (this.env.view.type === "form" && this.props.activeIds[0]) {
                this.gdriveItems = await this._getGoogleDocItems();
            } else {
                this.gdriveItems = [];
            }
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         * @returns {Promise<Object[]>}
         */
        async _getGoogleDocItems() {
            const items = await this.rpc({
                args: [this.env.action.res_model, this.props.activeIds[0]],
                context: this.props.context,
                method: 'get_google_drive_config',
                model: 'google.drive.config',
            });
            return items;
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {number} itemId
         * @returns {Promise}
         */
        async _onGoogleDocItemClick(itemId) {
            const resID = this.props.activeIds[0];
            const domain = [['id', '=', itemId]];
            const fields = ['google_drive_resource_id', 'google_drive_client_id'];
            const configs = await this.rpc({
                args: [domain, fields],
                method: 'search_read',
                model: 'google.drive.config',
            });
            const url = await this.rpc({
                args: [itemId, resID, configs[0].google_drive_resource_id],
                context: this.props.context,
                method: 'get_google_drive_url',
                model: 'google.drive.config',
            });
            if (url) {
                window.open(url, '_blank');
            }
        }
    }
    GoogleDriveMenu.props = {
        activeIds: Array,
        context: Object,
    };
    GoogleDriveMenu.template = 'GoogleDriveMenu';

    ActionMenus.registry.add('google-drive-menu', {
        Component: GoogleDriveMenu,
        getProps(parentProps) {
            return {
                activeIds: parentProps.activeIds,
                context: parentProps.context,
            };
        },
    });

    return GoogleDriveMenu;
});
