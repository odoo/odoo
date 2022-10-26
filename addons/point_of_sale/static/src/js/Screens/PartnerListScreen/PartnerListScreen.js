odoo.define('point_of_sale.PartnerListScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');

    const { debounce } = require("@web/core/utils/timing");
    const { useListener } = require("@web/core/utils/hooks");

    const { onWillUnmount, useRef, onMounted } = owl;

    /**
     * Render this screen using `showTempScreen` to select partner.
     * When the shown screen is confirmed ('Set Customer' or 'Deselect Customer'
     * button is clicked), the call to `showTempScreen` resolves to the
     * selected partner. E.g.
     *
     * ```js
     * const { confirmed, payload: selectedPartner } = await showTempScreen('PartnerListScreen');
     * if (confirmed) {
     *   // do something with the selectedPartner
     * }
     * ```
     *
     * @props partner - originally selected partner
     */
    class PartnerListScreen extends PosComponent {
        setup() {
            super.setup();
            useListener('click-save', () => this.env.bus.trigger('save-partner'));
            useListener('save-changes', this.saveChanges);
            this.searchWordInputRef = useRef('search-word-input-partner');

            // We are not using useState here because the object
            // passed to useState converts the object and its contents
            // to Observer proxy. Not sure of the side-effects of making
            // a persistent object, such as pos, into Observer. But it
            // is better to be safe.
            this.state = {
                query: null,
                selectedPartner: this.props.partner,
                detailIsShown: false,
                editModeProps: {
                    partner: null,
                },
            };
            this.updatePartnerList = debounce(this.updatePartnerList, 70);
            onWillUnmount(this.updatePartnerList.cancel);
            onMounted(() => {
                if(!this.env.pos.config.limited_partners_loading)
                    this.env.pos.isEveryPartnerLoaded = true;
            });

        }
        // Lifecycle hooks
        back() {
            if(this.state.detailIsShown) {
                this.state.detailIsShown = false;
                this.render(true);
            } else {
                this.props.resolve({ confirmed: false, payload: false });
                this.trigger('close-temp-screen');
            }
        }
        confirm() {
            this.props.resolve({ confirmed: true, payload: this.state.selectedPartner });
            this.trigger('close-temp-screen');
        }
        activateEditMode() {
            this.state.detailIsShown = true;
            this.render(true);
        }
        // Getters

        get currentOrder() {
            return this.env.pos.get_order();
        }

        get partners() {
            let res;
            if (this.state.query && this.state.query.trim() !== '') {
                res = this.env.pos.db.search_partner(this.state.query.trim());
            } else {
                res = this.env.pos.db.get_partners_sorted(1000);
            }
            res.sort(function (a, b) { return (a.name || '').localeCompare(b.name || '') });
            // the selected partner (if any) is displayed at the top of the list
            if (this.state.selectedPartner) {
                let indexOfSelectedPartner = res.findIndex( partner => 
                    partner.id === this.state.selectedPartner.id
                );
                if (indexOfSelectedPartner !== -1) {
                    res.splice(indexOfSelectedPartner, 1);
                    res.unshift(this.state.selectedPartner);
                }
            }
            return res
        }
        get isBalanceDisplayed() {
            return false;
        }
        get partnerLink() {
            return `/web#model=res.partner&id=${this.state.editModeProps.partner.id}`;
        }

        // Methods

        async _onPressEnterKey() {
            if (!this.state.query) return;
            if (!this.env.pos.isEveryPartnerLoaded) {
                const result = await this.searchPartner();
                this.showNotification(
                    _.str.sprintf(this.env._t('%s customer(s) found for "%s".'),
                        result.length,
                        this.state.query)
                    , 3000);
                if(!result.length) this._clearSearch();
            }
        }
        _clearSearch() {
            this.searchWordInputRef.el.value = '';
            this.state.query = '';
            this.render(true);
        }
        // We declare this event handler as a debounce function in
        // order to lower its trigger rate.
        async updatePartnerList(event) {
            this.state.query = event.target.value;
            if (event.code === 'Enter') {
                this._onPressEnterKey();
            } else {
                this.render(true);
            }
        }
        clickPartner(partner) {
            if (this.state.selectedPartner && this.state.selectedPartner.id === partner.id) {
                this.state.selectedPartner = null;
            } else {
                this.state.selectedPartner = partner;
            }
            this.confirm();
        }
        editPartner(partner) {
            this.state.editModeProps.partner = partner;
            this.activateEditMode();
        }
        createPartner() {
            // initialize the edit screen with default details about country & state
            this.state.editModeProps.partner = {
                country_id: this.env.pos.company.country_id,
                state_id: this.env.pos.company.state_id,
            }
            this.activateEditMode();
        }
        async saveChanges(event) {
            try {
                let partnerId = await this.rpc({
                    model: 'res.partner',
                    method: 'create_from_ui',
                    args: [event.detail.processedChanges],
                });
                await this.env.pos.load_new_partners();
                this.state.selectedPartner = this.env.pos.db.get_partner_by_id(partnerId);
                this.confirm();
            } catch (error) {
                if (isConnectionError(error)) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to save changes.'),
                    });
                } else {
                    throw error;
                }
            }
        }
        async searchPartner() {
            let result = await this.getNewPartners();
            this.env.pos.addPartners(result);
            if (!this.env.pos.isEveryPartnerLoaded) await this.env.pos.updateIsEveryPartnerLoaded();
            this.render(true);
            return result;
        }
        async getNewPartners() {
            let domain = [];
            if(this.state.query) {
                domain = ['|', ["name", "ilike", this.state.query + "%"],
                               ["parent_name", "ilike", this.state.query + "%"]];
            }
            const result = await this.env.services.rpc(
                {
                    model: 'pos.session',
                    method: 'get_pos_ui_res_partner_by_params',
                    args: [
                        [odoo.pos_session_id],
                        {
                            domain,
                            limit: 10,
                        },
                    ],
                    context: this.env.session.user_context,
                },
                {
                    timeout: 3000,
                    shadow: true,
                }
            );
            return result;
        }
    }
    PartnerListScreen.template = 'PartnerListScreen';

    Registries.Component.add(PartnerListScreen);

    return PartnerListScreen;
});
