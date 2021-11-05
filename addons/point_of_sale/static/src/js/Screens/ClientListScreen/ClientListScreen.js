odoo.define('point_of_sale.ClientListScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    /**
     * Render this screen using `showTempScreen` to select client.
     * When the shown screen is confirmed ('Set Customer' or 'Deselect Customer'
     * button is clicked), the call to `showTempScreen` resolves to the
     * selected client. E.g.
     *
     * ```js
     * const { confirmed, payload: selectedClient } = await showTempScreen('ClientListScreen');
     * if (confirmed) {
     *   // do something with the selectedClient
     * }
     * ```
     *
     * @props client - originally selected client
     */
    class ClientListScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click-save', this.saveChanges);
            useListener('click-edit', () => this.editClient());

            // We are not using useState here because the object
            // passed to useState converts the object and its contents
            // to Observer proxy. Not sure of the side-effects of making
            // a persistent object, such as pos, into owl.Observer. But it
            // is better to be safe.
            this.state = {
                query: null,
                selectedClient: this.props.client,
                detailIsShown: false,
                isEditMode: false,
                editModeProps: {
                    // default partner
                    partner: {
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                    },
                    changes: {},
                },
            };
            this.intFields = ['country_id', 'state_id', 'property_product_pricelist'];
            this.updateClientList = debounce(this.updateClientList, 70);
        }
        // Lifecycle hooks
        back() {
            if(this.state.detailIsShown) {
                this.state.detailIsShown = false;
                this.render();
            } else {
                this.props.resolve({ confirmed: false, payload: false });
                this.trigger('close-temp-screen');
            }
        }
        confirm() {
            this.props.resolve({ confirmed: true, payload: this.state.selectedClient });
            this.trigger('close-temp-screen');
        }
        // Getters

        get currentOrder() {
            return this.env.pos.get_order();
        }

        get clients() {
            let res;
            if (this.state.query && this.state.query.trim() !== '') {
                res = this.env.pos.db.search_partner(this.state.query.trim());
            } else {
                res = this.env.pos.db.get_partners_sorted(1000);
            }
            return res.sort(function (a, b) { return (a.name || '').localeCompare(b.name || '') });
        }
        get isNextButtonVisible() {
            return this.state.selectedClient ? true : false;
        }
        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.props.client) {
                return { command: 'set', text: this.env._t('Set Customer') };
            } else if (this.props.client && this.props.client.id === this.state.selectedClient.id) {
                return { command: 'deselect', text: this.env._t('Deselect Customer') };
            } else {
                return { command: 'set', text: this.env._t('Change Customer') };
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // order to lower its trigger rate.
        async updateClientList(event) {
            var newClientList = await this.getNewClient();
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                this.state.selectedClient = clients[0];
                this.clickNext();
            } else {
                this.render();
            }
        }
        clickClient(event) {
            let partner = event.detail.client;
            if (this.state.selectedClient === partner) {
                this.state.selectedClient = null;
            } else {
                this.state.selectedClient = partner;
            }
            this.render();
        }
        editClient() {
            this.state.editModeProps.partner = this.state.selectedClient;
            this.state.detailIsShown = true;
            this.render();
        }
        async clickNext() {
            if (this.isUnsavedChanges() && await this.isSaveWanted()) {
                await this.saveChanges();
            }
            this.state.selectedClient = this.nextButton.command === 'set' ? this.state.selectedClient : null;
            this.confirm();
        }
        isUnsavedChanges() {
            return Object.keys(this.state.editModeProps.changes).length > 0;
        }
        async isSaveWanted() {
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Unsaved changes'),
                body: this.env._t('Do you want to save your changes?'),
                confirmText: this.env._t('Yes'),
                cancelText: this.env._t('No'),
            });
            return confirmed;
        }
        activateEditMode(event) {
            const { isNewClient } = event.detail;
            if (isNewClient) {
                const { partner } = this.state.editModeProps;
                this.state.editModeProps.changes = {
                    'country_id': partner.country_id && partner.country_id[0],
                    'state_id': partner.state_id && partner.state_id[0],
                };
            } else {
                this.state.editModeProps.partner = this.state.selectedClient;
            }
            this.state.isEditMode = true;
            this.state.detailIsShown = true;
            this.state.isNewClient = isNewClient;
            this.render();
        }
        deactivateEditMode() {
            this.state.isEditMode = false;
            this.state.editModeProps = {
                partner: {
                    country_id: this.env.pos.company.country_id,
                    state_id: this.env.pos.company.state_id,
                },
            };
            this.render();
        }
        async saveChanges() {
            try {
                let processedChanges = {};
                for (let [key, value] of Object.entries(this.state.editModeProps.changes)) {
                    if (this.intFields.includes(key)) {
                        processedChanges[key] = parseInt(value) || false;
                    } else {
                        processedChanges[key] = value;
                    }
                }
                if ((!this.state.editModeProps.partner.name && !processedChanges.name) || processedChanges.name === '') {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('A Customer Name Is Required'),
                    });
                }
                processedChanges.id = this.state.editModeProps.partner.id || false;

                let partnerId = await this.rpc({
                    model: 'res.partner',
                    method: 'create_from_ui',
                    args: [processedChanges],
                });
                await this.env.pos.load_new_partners();
                this.state.selectedClient = this.env.pos.db.get_partner_by_id(partnerId);
                this.state.detailIsShown = false;
                this.render();
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to save changes.'),
                    });
                } else {
                    throw error;
                }
            } finally {
                this.state.editModeProps.changes = {};
            }
        }
        cancelEdit() {
            this.deactivateEditMode();
        }
        async searchClient() {
            let result = await this.getNewClient();
            this.env.pos.db.add_partners(result);
            if(!result.length) {
                await this.showPopup('ErrorPopup', {
                    title: '',
                    body: this.env._t('No customer found'),
                });
            }
            this.render();
        }
        async getNewClient() {
            var domain = [];
            if(this.state.query) {
                domain = [["name", "ilike", this.state.query + "%"]];
            }
            var fields = _.find(this.env.pos.models, function(model){ return model.label === 'load_partners'; }).fields;
            var result = await this.rpc({
                model: 'res.partner',
                method: 'search_read',
                args: [domain, fields],
                kwargs: {
                    limit: 10,
                },
            },{
                timeout: 3000,
                shadow: true,
            });

            return result;
        }
    }
    ClientListScreen.template = 'ClientListScreen';

    Registries.Component.add(ClientListScreen);

    return ClientListScreen;
});
