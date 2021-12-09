odoo.define('google_drive.ActionMenus', function (require) {
    "use strict";

    const ActionMenus = require('web.ActionMenus');
    const DropdownMenuItem = require('web.DropdownMenuItem');
    const { registry } = require("@web/core/registry");

    /**
     * @typedef {import("@web/env").OdooEnv} OdooEnv
     */

    /**
     * Fetches the google drive action menu item props. To do so this function
     * is given its parent props and env, as well as the RPC function bound to
     * the parent context.
     * Note that we use the bound RPC to benefit from its added behaviour (see
     * web/component_extension).
     * @param {Object} props
     * @param {number[]} props.activeIds
     * @param {Object} props.context
     * @param {OdooEnv} env
     * @returns {Object | boolean} item props or false
     */
    async function googleDrivePropsGetter(props, env) {
        const [activeId] = props.activeIds;
        const { context } = props;
        if (env.view.type !== "form" || !activeId) {
            return false;
        }
        const items = await env.services.rpc({
            args: [props.resModel, activeId],
            context,
            method: 'get_google_drive_config',
            model: 'google.drive.config',
        });
        return Boolean(items.length) && { activeId, context, items };
    }

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

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {number} itemId
         * @returns {Promise}
         */
        async _onGoogleDocItemClick(itemId) {
            const resID = this.props.activeId;
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
        activeId: Number,
        context: Object,
        items: {
            type: Array,
            element: Object,
        },
    };
    GoogleDriveMenu.template = 'GoogleDriveMenu';

    registry.category("action_menus").add('google-drive-menu', {
        Component: GoogleDriveMenu,
        getProps: googleDrivePropsGetter,
    });

    return GoogleDriveMenu;
});
