    odoo.define('point_of_sale.GiftVoucherScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    class GiftVoucherScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('close-screen', this.close);
            useListener('click-extend', () => this.extendExpireDate()); 
            useListener('click-recharge', () => this.rechargeGiftCard());
            useListener('click-exchange', () => this.ChangeCardGiftCard());
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
            this.state = {
                query: null,
                selectedVoucher: this.props.gift_voucher,
                detailIsShown: false,
                isEditMode: false,
                editModeProps: {
                    partner: {
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                    }
                },
            }
        }
        
        close(){
            this.showScreen('ProductScreen');
        }
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }
        async clickVoucher(event) {
            let Voucher = event.detail.voucher;
            if (this.state.selectedVoucher === Voucher) {
                // this.state.selectedVoucher = null;
            } else {
                this.state.selectedVoucher = Voucher;
            }
            await this.rpc({
                model: 'aspl.gift.voucher.redeem',
                method: 'search_read',
                domain: [['voucher_id', '=', this.state.selectedVoucher.id]],
            }, {async: true}).then((gift_voucher) => {
                this.test = gift_voucher
            })
            this.VoucherHistory = this.test
            this.render();
        }

        get highlight() {
            return this.state.selectedVoucher !== this.state.selectedVoucher ? '' : 'highlight';
        }
        // Lifecycle hooks
        back() {
            if(this.state.detailIsShown) {
                this.state.detailIsShown = false;
                this.render();
            } else {
                this.trigger('close-screen');
            }
        }
        get GiftVoucherList() {
            return this.env.pos.gift_vouchers;
        }
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        get filteredGiftVoucherList() {
            const { fieldValue, searchTerm } = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (order) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return searchCheck(order);
            };
            return this.GiftVoucherList.filter(predicate);
        }
        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }
        get filterOptions() {
            return ['Voucher', 'History'];
        }
        
        get _searchFields() {
            var fields = {}
            fields = {
                'Voucher Number': (order) => order.voucher_code,
                'voucher Name': (order) => order.voucher_name,
                'Minimum Purcher Amount': (order) => order.minimum_purchase,
                'Expire Date(YYYY-MM-DD hh:mm A)': (order) => moment(order.expiry_date).format('YYYY-MM-DD hh:mm A'),
            };
            return fields;
        }
        get _screenToStatusMap() {
            return {
                ProductScreen: 'History',
                PaymentScreen: 'Voucher',
            };
        }
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
                screenToStatusMap: this._screenToStatusMap,
            });
        }
    }
    GiftVoucherScreen.template = 'GiftVoucherScreen';

    Registries.Component.add(GiftVoucherScreen);

    return GiftVoucherScreen;
});
 