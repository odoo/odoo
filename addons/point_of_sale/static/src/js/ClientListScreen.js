odoo.define('point_of_sale.ClientListScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const { useRef } = owl.hooks;
    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');
    const { ClientLine } = require('point_of_sale.ClientLine');
    const { ClientDetails } = require('point_of_sale.ClientDetails');
    const { ClientDetailsEdit } = require('point_of_sale.ClientDetailsEdit');

    class ClientListScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = {
                query: null,
                selectedClient: this.currentOrderClient,
                detailIsShown: Boolean(this.currentOrderClient),
                isEditMode: false,
                editModeProps: {
                    partner: {
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                    },
                    pos: this.env.pos,
                },
            };
            // TODO jcb: to remove
            // These refs are attempts to fix the problem on unshown list
            // items when the customer details are shown.
            this.clientListRef = useRef('client-list-ref');
            this.clientDetailsRef = useRef('client-details-ref');
            this.updateClientList = debounce(this.updateClientList, 70);
        }

        // Lifecycle hooks

        mounted() {
            this.env.pos.on(
                'change:selectedOrder',
                () => {
                    // RECOMMENDATION
                    // perhaps there is a better way than resetting the state.
                    // maybe we save the clientlistscreen ui state in the current order
                    // so that when we return to a viewed order, we resume to its
                    // previous state. e.g. if we are in edit mode in order 1, then we open
                    // order 2, then we go back to order 1, the client list screen should
                    // return to edit mode state.
                    this._resetState();
                },
                this
            );
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrder', null, this);
        }
        back() {
            this.props.resolve({ confirmed: false, payload: false });
            this.trigger('close-temp-screen');
        }
        confirm() {
            this.props.resolve({ confirmed: true, payload: true });
            this.trigger('close-temp-screen');
        }
        // Getters

        get currentOrder() {
            return this.env.pos.get_order();
        }

        get currentOrderClient() {
            return this.currentOrder.get_client();
        }
        get clients() {
            if (this.state.query && this.state.query.trim() !== '') {
                return this.env.pos.db.search_partner(this.state.query.trim());
            } else {
                return this.env.pos.db.get_partners_sorted(1000);
            }
        }
        get isNextButtonVisible() {
            return this.state.selectedClient ? !this.state.isEditMode : false;
        }
        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.currentOrderClient) {
                return { command: 'set', text: 'Set Customer' };
            } else if (
                this.currentOrderClient &&
                this.currentOrderClient === this.state.selectedClient
            ) {
                return { command: 'deselect', text: 'Deselect Customer' };
            } else {
                return { command: 'set', text: 'Change Customer' };
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // order to lower its trigger rate.
        updateClientList(event) {
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
                this.state.detailIsShown = !this.state.detailIsShown;
            } else {
                this.state.selectedClient = partner;
                this.state.detailIsShown = true;
            }
            this.deactivateEditMode();
        }
        clickNext() {
            const newClient = this.nextButton.command === 'set' ? this.state.selectedClient : null;
            this._updateOrderPricelist(newClient);
            this.currentOrder.set_client(newClient);
            this.back();
        }
        activateEditMode(event) {
            const { isNewClient } = event.detail;
            this.state.isEditMode = true;
            this.state.detailIsShown = true;
            if (!isNewClient) {
                this.state.editModeProps = {
                    partner: this.state.selectedClient,
                    pos: this.env.pos,
                };
            }
            this.render();
        }
        deactivateEditMode() {
            this.state.isEditMode = false;
            // TODO jcb: set default values here?
            this.state.editModeProps = {
                partner: {
                    country_id: this.env.pos.company.country_id,
                    state_id: this.env.pos.company.state_id,
                },
                pos: this.env.pos,
            };
            this.render();
        }
        async saveChanges(event) {
            try {
                let partnerId = await this.rpc({
                    model: 'res.partner',
                    method: 'create_from_ui',
                    args: [event.detail.processedChanges],
                });
                await this.env.pos.load_new_partners();
                this.state.selectedClient = this.env.pos.db.get_partner_by_id(partnerId);
                if (
                    this.currentOrderClient &&
                    this.state.selectedClient.id === this.currentOrderClient.id
                ) {
                    this.currentOrder.set_client(this.state.selectedClient);
                }
                this.deactivateEditMode();
            } catch (err) {
                // TODO jcb: what is the proper error message?
                console.error(err);
            }
        }
        cancelEdit() {
            this.deactivateEditMode();
        }
        _updateOrderPricelist(newClient) {
            let newClientPricelist, newClientFiscalPosition;
            const defaultFiscalPosition = this.env.pos.fiscal_positions.find(
                position => position.id === this.env.pos.config.default_fiscal_position_id[0]
            );
            if (newClient) {
                newClientFiscalPosition = newClient.property_account_position_id
                    ? this.env.pos.fiscal_positions.find(
                          position => position.id === newClient.property_account_position_id[0]
                      )
                    : defaultFiscalPosition;
                newClientPricelist =
                    this.env.pos.pricelists.find(
                        pricelist => pricelist.id === newClient.property_product_pricelist[0]
                    ) || this.env.pos.default_pricelist;
            } else {
                newClientFiscalPosition = defaultFiscalPosition;
                newClientPricelist = this.env.pos.default_pricelist;
            }
            this.currentOrder.fiscal_position = newClientFiscalPosition;
            this.currentOrder.set_pricelist(newClientPricelist);
        }
        _resetState() {
            this.state.query = null;
            this.state.selectedClient = this.currentOrderClient;
            this.state.detailIsShown = true;
            this.state.isEditMode = false;
            this.state.editModeProps = {};
            this.render();
        }
    }

    addComponents(ClientListScreen, [ClientLine, ClientDetails, ClientDetailsEdit]);
    addComponents(Chrome, [ClientListScreen]);

    return { ClientListScreen };
});
