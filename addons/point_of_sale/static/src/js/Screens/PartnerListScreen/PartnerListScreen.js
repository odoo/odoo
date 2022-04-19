odoo.define('point_of_sale.PartnerListScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');
    const { useAsyncLockedMethod } = require('point_of_sale.custom_hooks');

    const { debounce } = require("@web/core/utils/timing");
    const { useListener } = require("@web/core/utils/hooks");

    const { onWillUnmount } = owl;

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
            this.lockedSaveChanges = useAsyncLockedMethod(this.saveChanges);
            useListener('click-save', () => this.env.bus.trigger('save-partner'));
            useListener('click-edit', () => this.editPartner());
            useListener('save-changes', this.lockedSaveChanges);

            // We are not using useState here because the object
            // passed to useState converts the object and its contents
            // to Observer proxy. Not sure of the side-effects of making
            // a persistent object, such as pos, into Observer. But it
            // is better to be safe.
            this.state = {
                query: null,
                selectedPartner: this.props.partner,
                detailIsShown: false,
                // isEditMode: false,
                editModeProps: {
                    partner: {
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                    }
                },
            };
            this.updatePartnerList = debounce(this.updatePartnerList, 70);
            onWillUnmount(this.updatePartnerList.cancel);
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
            return res.sort(function (a, b) { return (a.name || '').localeCompare(b.name || '') });
        }
        get isNextButtonVisible() {
            return this.state.selectedPartner ? true : false;
        }
        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.props.partner) {
                return { command: 'set', text: this.env._t('Set Customer') };
            } else if (this.props.partner && this.props.partner === this.state.selectedPartner) {
                return { command: 'deselect', text: this.env._t('Deselect Customer') };
            } else {
                return { command: 'set', text: this.env._t('Change Customer') };
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // order to lower its trigger rate.
        async updatePartnerList(event) {
            this.state.query = event.target.value;
            const partners = this.partners;
            if (event.code === 'Enter' && partners.length === 1) {
                this.state.selectedPartner = partners[0];
                this.clickNext();
            } else {
                this.render(true);
            }
        }
        clickPartner(partner) {
            if (this.state.selectedPartner === partner) {
                this.state.selectedPartner = null;
            } else {
                this.state.selectedPartner = partner;
            }
            this.render(true);
        }
        editPartner() {
            this.state.editModeProps = {
                partner: this.state.selectedPartner,
            };
            this.state.detailIsShown = true;
            this.render(true);
        }
        clickNext() {
            this.state.selectedPartner = this.nextButton.command === 'set' ? this.state.selectedPartner : null;
            this.confirm();
        }
        activateEditMode(isNewPartner) {
            // this.state.isEditMode = true;
            this.state.detailIsShown = true;
            this.state.isNewPartner = isNewPartner;
            if (!isNewPartner) {
                this.state.editModeProps = {
                    partner: this.state.selectedPartner,
                };
            }
            this.render(true);
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
                this.state.detailIsShown = false;
                this.render(true);
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
            this.env.pos.db.add_partners(result);
            if(!result.length) {
                await this.showPopup('ErrorPopup', {
                    title: '',
                    body: this.env._t('No customer found'),
                });
            }
            this.render(true);
        }
        async getNewPartners() {
            let domain = [];
            if(this.state.query) {
                domain = [["name", "ilike", this.state.query + "%"]];
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
