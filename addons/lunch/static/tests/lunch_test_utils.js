odoo.define('lunch.test_utils', function (require) {
"use strict";

const AbstractStorageService = require('web.AbstractStorageService');
const RamStorage = require('web.RamStorage');
const {createView} = require('web.test_utils');

/**
 * Helper to create a lunch kanban view with searchpanel
 *
 * @param {object} params
 */
async function createLunchKanbanView(params) {
    const archPieces = params.arch.split('</templates>');
    params.arch = `
        ${archPieces[0]}</templates>
        <searchpanel>
            <field name="category_id" select="multi" string="Categories"/>
            <field name="supplier_id" select="multi" string="Vendors"/>
        </searchpanel>
        ${archPieces[1]}
    `;
    if (!params.services || !params.services.local_storage) {
        // the searchPanel uses the localStorage to store/retrieve default
        // active category value
        params.services = params.services || {};
        const RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
        params.services.local_storage = RamStorageService;
    }
    return createView(params);
}

/**
 * Helper to generate a mockRPC function for the mandatory lunch routes (prefixed by '/lunch')
 *
 * @param {object} infos
 * @param {integer} userLocation
 */
function mockLunchRPC({infos, userLocation}) {
    return async function (route) {
        if (route === '/lunch/infos') {
            return Promise.resolve(infos);
        }
        if (route === '/lunch/user_location_get') {
            return Promise.resolve(userLocation);
        }
        return this._super.apply(this, arguments);
    };
}

return {
    createLunchKanbanView,
    mockLunchRPC,
};

});
