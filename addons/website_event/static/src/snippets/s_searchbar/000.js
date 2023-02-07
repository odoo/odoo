/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.searchBar.include({
    /**
     *
     * @override
     */
    _getFieldsNames() {
        return [...this._super(), 'address_name'];
    }
});
