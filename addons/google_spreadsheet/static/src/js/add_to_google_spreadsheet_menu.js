odoo.define('board.AddToGoogleSpreadsheetMenu', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const DropdownMenuItem = require('web.DropdownMenuItem');
    const FavoriteMenu = require('web.FavoriteMenu');

    /**
     * 'Add to Google spreadsheet' menu
     *
     * Component consisting only of a button calling the server to add the current
     * view to the user's spreadsheet configuration.
     * This component is only available in actions of type 'ir.actions.act_window'.
     * @extends DropdownMenuItem
     */
    class AddToGoogleSpreadsheetMenu extends DropdownMenuItem {

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        async _onAddToSpreadsheet() {
            const searchQuery = this.env.searchModel.get('query');
            const listView = this.env.action.views.find(view => view.type === 'list');
            const modelName = this.env.action.res_model;
            const domain = Domain.prototype.arrayToString(searchQuery.domain);
            const groupBys = searchQuery.groupBy.join(" ");
            const listViewId = listView ? listView.viewID : false;
            const result = await this.rpc({
                model: 'google.drive.config',
                method: 'set_spreadsheet',
                args: [modelName, domain, groupBys, listViewId],
            });
            if (result.url) {
                // According to MDN doc, one should not use _blank as title.
                // todo: find a good name for the new window
                window.open(result.url, '_blank');
            }
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @param {Object} env
         * @returns {boolean}
         */
        static shouldBeDisplayed(env) {
            return env.action.type === 'ir.actions.act_window';
        }
    }

    AddToGoogleSpreadsheetMenu.props = {};
    AddToGoogleSpreadsheetMenu.template = 'AddToGoogleSpreadsheetMenu';

    FavoriteMenu.registry.add('add-to-google-spreadsheet-menu', AddToGoogleSpreadsheetMenu, 20);

    return AddToGoogleSpreadsheetMenu;
});
