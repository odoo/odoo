odoo.define('board.AddToGoogleSpreadsheetMenu', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const { DropdownItem } = require('@web/core/dropdown/dropdown_item');
    const FavoriteMenu = require('web.FavoriteMenu');

    const Dialog = require('web.Dialog');
    const { Component } = owl;

    const { qweb } = require('web.core');

    /**
     * 'Add to Google spreadsheet' menu
     *
     * Component consisting only of a button calling the server to add the current
     * view to the user's spreadsheet configuration.
     * This component is only available in actions of type 'ir.actions.act_window'.
     */
    class AddToGoogleSpreadsheetMenu extends Component {
        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        async addToGoogleSpreadsheet() {
            const searchQuery = this.env.searchModel.get('query');
            const listView = this.env.action.views.find(view => view.type === 'list');
            const modelName = this.env.action.res_model;
            const domain = Domain.prototype.arrayToString(searchQuery.domain);
            const groupBys = searchQuery.groupBy.join(" ");
            const listViewId = listView ? listView.viewID : false;
            const result = await this.env.services.rpc({
                model: 'google.drive.config',
                method: 'set_spreadsheet',
                args: [modelName, domain, groupBys, listViewId],
            });

            if (result.deprecated) {
                return new Dialog(this, {
                    size: 'large',
                    $content: qweb.render('google_spreadsheet.FormulaDialog', {
                        url: result.url,
                        formula: result.formula,
                    }),
                    title: 'Google Spreadsheet',
                }).open();
            }
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
    AddToGoogleSpreadsheetMenu.template = "google_spreadsheet.AddToGoogleSpreadsheet";
    AddToGoogleSpreadsheetMenu.components = { DropdownItem };

    FavoriteMenu.registry.add('add-to-google-spreadsheet-menu', AddToGoogleSpreadsheetMenu, 20);

    return AddToGoogleSpreadsheetMenu;
});
