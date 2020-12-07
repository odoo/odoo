/** @odoo-module alias=point_of_sale.BasicSearchBar **/

const { useState, onMounted, onWillUnmount } = owl.hooks;
const { Component } = owl;

class BasicSearchBar extends Component {
    constructor() {
        super(...arguments);
        this._state = useState({ show: false, searchTerm: '' });
        this._activeConfig = false;
        this._configStack = [];
    }
    _onInputKeyUp(event) {
        if (this._activeConfig) {
            this._state.searchTerm = event.target.value;
            this._activeConfig.onSearchTermChange([this._state.searchTerm, event.key]);
        }
    }
    _onClickClear() {
        if (this._activeConfig) {
            this._state.searchTerm = '';
            this._activeConfig.onSearchTermChange([this._state.searchTerm]);
        }
    }
    /**
     * @param {object} config
     * @param {Function} config.onSearchTermChange
     * @param {string} config.searchTerm
     * @param {string} config.placeholder
     * @return {Function} method to clear the search term.
     */
    useSearchBar(config) {
        config.searchTerm = config.searchTerm || '';
        config.placeholder = config.placeholder || 'Search...';
        config.onSearchTermChange = config.onSearchTermChange
            ? config.onSearchTermChange.bind(Component.current)
            : () => {};
        onMounted(() => {
            const prevConfig = this._activeConfig;
            if (prevConfig) {
                prevConfig.searchTerm = this._state.searchTerm;
            }
            this._configStack.push(config);
            const newConfig = this._configStack[this._configStack.length - 1];
            this._state.show = true;
            this._state.searchTerm = newConfig.searchTerm;
            if (newConfig.searchTerm) {
                newConfig.onSearchTermChange([this._state.searchTerm]);
            }
            this._activeConfig = newConfig;
        });
        onWillUnmount(() => {
            this._configStack.pop();
            const configToActivate = this._configStack[this._configStack.length - 1] || false;
            if (!configToActivate) {
                this._state.show = false;
                this._state.searchTerm = '';
            } else {
                this._state.searchTerm = configToActivate.searchTerm;
            }
            this._activeConfig = configToActivate;
        });
        return () => {
            this._onClickClear();
        };
    }
}
BasicSearchBar.template = 'point_of_sale.BasicSearchBar';

export default BasicSearchBar;
