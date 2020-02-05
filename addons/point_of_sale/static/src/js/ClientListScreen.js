odoo.define('point_of_sale.ClientListScreen', function(require) {
    'use strict';

    const utils = require('web.utils');
    const { debounce } = owl.utils;
    const { useRef } = owl.hooks;
    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent } = require('point_of_sale.PosComponent');

    class ClientLine extends PosComponent {
        constructor() {
            super(...arguments);
        }
        get highlight() {
            if (this.props.partner !== this.props.selectedClient) {
                return '';
            } else {
                return this.props.isShowDetails ? 'highlight' : 'lowlight';
            }
        }
    }

    class ClientDetails extends PosComponent {
        constructor() {
            super(...arguments);
        }
        get partnerImageUrl() {
            if (this.props.partner) {
                return `/web/image?model=res.partner&id=${this.props.partner.id}&field=image_128`;
            } else {
                return false;
            }
        }
    }

    class ClientDetailsEdit extends PosComponent {
        constructor() {
            super(...arguments);
            this.intFields = ['country_id', 'state_id', 'property_product_pricelist'];
            this.changes = {};
        }
        get partnerImageUrl() {
            // We prioritize image_1920 in the `changes` field because we want
            // to show the uploaded image without fetching new data from the server.
            if (this.changes.image_1920) {
                return this.changes.image_1920;
            } else if (this.props.partner.id) {
                return `/web/image?model=res.partner&id=${this.props.partner.id}&field=image_128`;
            } else {
                return false;
            }
        }
        /**
         * Save to field `changes` all input changes from the form fields.
         */
        captureChange(event) {
            this.changes[event.target.name] = event.target.value;
        }
        saveChanges() {
            let processedChanges = {};
            for (let [key, value] of Object.entries(this.changes)) {
                if (this.intFields.includes(key)) {
                    processedChanges[key] = parseInt(value) || false;
                } else {
                    processedChanges[key] = value;
                }
            }
            processedChanges.id = this.props.partner.id || false;
            this.trigger('save-changes', { processedChanges });
        }
        async uploadImage(event) {
            const file = event.target.files[0];
            try {
                if (!file.type.match(/image.*/)) {
                    throw {
                        name: 'UnsupportedFileFormat',
                        message: {
                            title: _t('Unsupported File Format'),
                            body: _t(
                                'Only web-compatible Image formats such as .png or .jpeg are supported.'
                            ),
                        },
                    };
                }
                const imageUrl = await utils.getDataURLFromFile(file);
                const loadedImage = await this._loadImage(imageUrl);
                const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                this.changes.image_1920 = resizedImage.toDataURL();
                // Rerender to reflect the changes in the screen
                this.render();
            } catch (err) {
                // TODO jcb: show popup instead of console error
                switch (err.name) {
                    // can be error from FileReader abort or error
                    case 'UnsupportedFileFormat':
                    case 'LoadingImageError':
                        // ErrorPopup.show(err.message);
                        break;
                    default:
                        console.error(['Unhandled Error', err]);
                        break;
                }
            }
        }
        _resizeImage(img, maxwidth, maxheight) {
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            var ratio = 1;

            if (img.width > maxwidth) {
                ratio = maxwidth / img.width;
            }
            if (img.height * ratio > maxheight) {
                ratio = maxheight / img.height;
            }
            var width = Math.floor(img.width * ratio);
            var height = Math.floor(img.height * ratio);

            canvas.width = width;
            canvas.height = height;
            ctx.drawImage(img, 0, 0, width, height);
            return canvas;
        }
        /**
         * Loading image is converted to a Promise to allow await when
         * loading an image. It resolves to the loaded image.
         *
         * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
         */
        _loadImage(url) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.addEventListener('load', () => resolve(img));
                img.addEventListener('error', () =>
                    reject({
                        name: 'LoadingImageError',
                        message: {
                            title: 'Loading Image Error',
                            body: 'We encountered error when loading image. Please try again.',
                        },
                    })
                );
                img.src = url;
            });
        }
    }

    class ClientListScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.gui = this.props.gui;
            this.state = {
                query: null,
                selectedClient: this.currentOrderClient,
                isShowDetails: Boolean(this.currentOrderClient),
                isEditMode: false,
                editModeProps: {
                    partner: {
                        country_id: this.pos.company.country_id,
                        state_id: this.pos.company.state_id,
                    },
                    pos: this.pos,
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
            this.pos.on('change:selectedOrder', () => {
                // RECOMMENDATION
                // perhaps there is a better way than resetting the state.
                // maybe we save the clientlistscreen ui state in the current order
                // so that when we return to a viewed order, we resume to its
                // previous state. e.g. if we are in edit mode in order 1, then we open
                // order 2, then we go back to order 1, the client list screen should
                // return to edit mode state.
                this._resetState();
            });
        }
        willUnmount() {
            this.pos.off('change:selectedOrder');
        }

        // Getters

        get currentOrderClient() {
            return this.pos.get_order().get_client();
        }
        get clients() {
            if (this.state.query && this.state.query.trim() !== '') {
                return this.pos.db.search_partner(this.state.query.trim());
            } else {
                return this.pos.db.get_partners_sorted(1000);
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
                this.state.isShowDetails = !this.state.isShowDetails;
            } else {
                this.state.selectedClient = partner;
                this.state.isShowDetails = true;
            }
            this.deactivateEditMode();
        }
        clickNext() {
            if (this.nextButton.command === 'set') {
                this.pos.get_order().set_client(this.state.selectedClient);
            } else if (this.nextButton.command === 'deselect') {
                this.pos.get_order().set_client(null);
            }
            this.trigger('show-screen', { name: 'ProductScreen' });
        }
        activateEditMode(event) {
            const { isNewClient } = event.detail;
            this.state.isEditMode = true;
            this.state.isShowDetails = true;
            if (!isNewClient) {
                this.state.editModeProps = { partner: this.state.selectedClient, pos: this.pos };
            }
            this.render();
        }
        deactivateEditMode() {
            this.state.isEditMode = false;
            // TODO jcb: set default values here?
            this.state.editModeProps = {
                partner: {
                    country_id: this.pos.company.country_id,
                    state_id: this.pos.company.state_id,
                },
                pos: this.pos,
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
                await this.pos.load_new_partners();
                this.state.selectedClient = this.pos.db.get_partner_by_id(partnerId);
                if (
                    this.currentOrderClient &&
                    this.state.selectedClient.id === this.currentOrderClient.id
                ) {
                    this.pos.get_order().set_client(this.state.selectedClient);
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
        _resetState() {
            this.state.query = null;
            this.state.selectedClient = this.currentOrderClient;
            this.state.isShowDetails = true;
            this.state.isEditMode = false;
            this.state.editModeProps = {};
            this.render();
        }
    }
    ClientListScreen.addComponents([ClientLine, ClientDetails, ClientDetailsEdit]);

    Chrome.addComponents([ClientListScreen]);

    return { ClientListScreen, ClientLine, ClientDetails, ClientDetailsEdit };
});
