import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.searchBar.include({
    /**
     *
     * @override
     */
    _getFieldsNames() {
        return [...this._super(), 'address_name'];
    }
});
