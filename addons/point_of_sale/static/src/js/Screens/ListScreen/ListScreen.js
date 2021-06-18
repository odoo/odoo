odoo.define('point_of_sale.ListScreen', function (require) {
    'use strict';

    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    const NUMBER_TYPES = ['monetary', 'int', 'float'];
    const FIELDS_INFO_CACHE = {};

    /**
     * INSTRUCTIONS
     * ------------
     * To add a list in ListScreen, one should extend this class in-place.
     * 1. Create a method that will return the `ListInfo` of the list you want to show.
     *  It's basically the metadata of the list to be rendered.
     *  The `ListInfo` should contain the following properties:
     *      * `name`: unique name of the list
     *      * `model`: name of the model
     *      * `getRecordDisplayDetailsMethod` [optional]: method name that returns the display details of each record.
     *          Takes as first argument the generated default record details and as 2nd argument record itself.
     *      * `getFetchKwargsMethod` [optional]: by default, kwargs for search_read is generated in `_getFetchDefaultKwargs`.
     *          This method will be used to augment the result of the default kwargs.
     *      * `onClickRecordMethod`: this is the method to be called when a record is clicked in the list.
     *      * `fieldsToLoad`: this is the list of field names to load
     *      * `fieldsToShow`: this is the field names that will be displayed as columns in the list. defaults to `fieldsToLoad`.
     *      * `nPerPage`: this is the number of records shown per page in the list.
     * 2. Define the methods specified in the `ListInfo` returned in 1.
     * 3. Override `_getListInfoGetters` to make sure its return includes the name of the method defined in 1.
     */
    class ListScreen extends IndependentToOrderScreen {
        constructor() {
            super(...arguments);
            this.setListeners();
            this.state = owl.hooks.useState({ searchString: '' });
            this.listInfos = this._initListInfos();
            this.activeListInfo = false;
        }
        setListeners() {
            useListener('close-screen', this.close);
            useListener('set-list-info', this._setActiveListInfo);
            useListener('click-record', this._onClickRecord);
            useListener('clear-search', this._onClearSearch);
            useListener('search', this._onSearch);
            useListener('set-page', this._onSetPage);
        }
        async willStart() {
            if (this.props.defaultListId) {
                const listInfo = this.listInfos[this.props.defaultListId];
                listInfo.fieldsInfo = await this._getFieldsInfo(listInfo);
            }
        }
        mounted() {
            if (this.props.defaultListId) {
                this._setActiveListInfo({ detail: this.listInfos[this.props.defaultListId] });
            }
        }
        onInputKeydown(event) {
            if (this.activeListInfo && event.key === 'Enter') {
                this.trigger('search', this.state.searchString);
            }
        }
        async _getFieldsInfo(listInfo) {
            if (!(listInfo.id in FIELDS_INFO_CACHE)) {
                FIELDS_INFO_CACHE[listInfo.id] = await this.rpc({
                    model: listInfo.model,
                    method: 'fields_get',
                    args: [listInfo.fieldsToLoad],
                });
            }
            return FIELDS_INFO_CACHE[listInfo.id];
        }
        _initListInfos() {
            const getters = this._getListInfoGetters();
            const listInfos = [];
            for (const getter of getters) {
                if (!this[getter]) continue;
                const defaults = {
                    currentPage: 1,
                    nPerPage: 20,
                    searchTerm: '',
                };
                const listInfo = Object.assign(defaults, this[getter].call(this));
                listInfos.push([listInfo.id, listInfo]);
            }
            return Object.fromEntries(listInfos);
        }
        async _setActiveListInfo(event) {
            this.activeListInfo = event.detail;
            if (!this.activeListInfo.fieldsToShow) {
                this.activeListInfo.fieldsToShow = this.activeListInfo.fieldsToLoad;
            }
            if (!this.activeListInfo.fieldsInfo) {
                this.activeListInfo.fieldsInfo = await this._getFieldsInfo(this.activeListInfo);
            }
            this.state.searchString = this.activeListInfo.searchTerm;
            return this._fetch();
        }
        _onClickRecord(event) {
            if (!this.activeListInfo) return;
            return this[this.activeListInfo.onClickRecordMethod].call(this, event.detail);
        }
        _onClearSearch() {
            this.state.searchString = '';
            this.activeListInfo.searchTerm = '';
            this.activeListInfo.currentPage = 1;
            return this._fetch();
        }
        _onSearch(event) {
            if (!this.activeListInfo) return;
            this.activeListInfo.searchTerm = event.detail;
            this.activeListInfo.currentPage = 1;
            return this._fetch();
        }
        _onSetPage(event) {
            let newPage = 0;
            const param = event.detail;
            if (param.increment) {
                newPage = this.activeListInfo.currentPage + param.increment;
            } else if (param.to) {
                newPage = param.to;
            }
            this.activeListInfo.currentPage = newPage;
            return this._fetch();
        }
        /**
         * Return the default kwargs for fetching records from the server. The `_fetch` method
         * starts with this value and it is overrided by the `getFetchKwargsMethod` of the activeListInfo.
         */
        _getFetchDefaultKwargs() {
            return {
                domain: [],
                fields: this.activeListInfo.fieldsToLoad,
                limit: this.activeListInfo.nPerPage,
                offset: (this.activeListInfo.currentPage - 1) * this.activeListInfo.nPerPage,
            };
        }
        async _fetch() {
            const defaultKwargs = this._getFetchDefaultKwargs();
            const getFetchKwargsMethod = this[this.activeListInfo.getFetchKwargsMethod];
            const kwargs = Object.assign(defaultKwargs, getFetchKwargsMethod ? getFetchKwargsMethod.call(this) : {});
            this.activeListInfo.totalCount = await this.rpc({
                method: 'search_count',
                model: this.activeListInfo.model,
                args: [kwargs.domain],
            });
            const records = await this.rpc({
                method: 'search_read',
                model: this.activeListInfo.model,
                kwargs,
            });
            this.activeListInfo.items = records;
            this.render();
        }
        isAtFirstPage() {
            if (!this.activeListInfo) return true;
            return this.activeListInfo.currentPage === 1;
        }
        isAtLastPage() {
            if (!this.activeListInfo) return true;
            const lastPage = this._getLastPage();
            return this.activeListInfo.currentPage >= lastPage;
        }
        _getLastPage() {
            const modulo = this.activeListInfo.totalCount % this.activeListInfo.nPerPage;
            const quotient = this.activeListInfo.totalCount / this.activeListInfo.nPerPage;
            return modulo === 0 ? quotient : Math.trunc(quotient) + 1;
        }
        getPageNumber() {
            const lastPage = this._getLastPage();
            if (isNaN(lastPage) || !lastPage) {
                return '';
            } else {
                return `(${this.activeListInfo.currentPage}/${lastPage})`;
            }
        }
        _defaultRecordDisplayDetails(record) {
            const result = {};
            const fieldsInfo = this.activeListInfo.fieldsInfo;
            for (const key of this.activeListInfo.fieldsToShow) {
                const fieldValue = {
                    classes: {},
                    text: '',
                };
                const fieldInfo = fieldsInfo[key];
                if (NUMBER_TYPES.includes(fieldInfo.type)) {
                    fieldValue.classes['pos-right-align'] = true;
                } else {
                    fieldValue.classes['pos-left-align'] = true;
                }
                if (fieldInfo.type === 'monetary') {
                    fieldValue.text = this.env.pos.format_currency(record[key]);
                } else if (fieldInfo.type === 'many2one') {
                    fieldValue.text = record[key] ? record[key][1] : '';
                } else {
                    fieldValue.text = record[key] || '';
                }
                result[key] = fieldValue;
            }
            return result;
        }
        /**
         * Returns an object that represents the display of the given record. It maps each
         * fieldToShow to corresponding object that contains `classes` and `text` properties.
         * @param {object} record
         * @returns {{ [fieldName]: { classes: { [className]: boolean }, text: string }}}
         */
        getRecordDisplayDetails(record) {
            const defaultDetails = this._defaultRecordDisplayDetails(record);
            const customGetRecordDisplayDetails = this.activeListInfo.getRecordDisplayDetailsMethod
                ? this[this.activeListInfo.getRecordDisplayDetailsMethod]
                : false;
            if (customGetRecordDisplayDetails) {
                return customGetRecordDisplayDetails.call(this, defaultDetails, record);
            } else {
                return defaultDetails;
            }
        }
        getHeaderDisplayDetails(fieldName) {
            const fieldInfo = this.activeListInfo.fieldsInfo[fieldName];
            const headerValue = {
                classes: {},
                text: fieldInfo.string,
            };
            if (NUMBER_TYPES.includes(fieldInfo.type)) {
                headerValue.classes['pos-right-align'] = true;
            } else {
                headerValue.classes['pos-left-align'] = true;
            }
            return headerValue;
        }
        /**
         * Should return a list of method names that will return the `ListInfo`s.
         * They are method names so that during construction of this component,
         * each `ListInfo` can derive values from the PosModel.
         * @returns {string[]}
         */
        _getListInfoGetters() {
            return [];
        }
    }
    ListScreen.template = 'point_of_sale.ListScreen';

    Registries.Component.add(ListScreen);

    return ListScreen;
});
