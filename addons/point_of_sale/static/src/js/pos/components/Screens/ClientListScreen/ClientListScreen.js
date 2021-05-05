/** @odoo-module alias=point_of_sale.ClientListScreen **/

const { debounce } = owl.utils;
import PosComponent from 'point_of_sale.PosComponent';

/**
 * IMPROVEMENT: this component needs pagination. It should only show limited number
 * of partners to prevent clogging the rendering.
 *
 * Render this screen using `showTempScreen` to select client.
 * When the shown screen is confirmed ('Set Customer' or 'Deselect Customer'
 * button is clicked), the call to `showTempScreen` resolves to the
 * selected client. E.g.
 *
 * ```js
 * const [confirmed, selectedClientId] = await showTempScreen('ClientListScreen');
 * if (confirmed) {
 *   // do something with the selectedClientId
 * }
 * ```
 *
 * @props clientId - originally selected client id
 */
class ClientListScreen extends PosComponent {
    constructor() {
        super(...arguments);
        this.state = owl.useState({
            query: '',
            selectedClientId: this.props.clientId,
            detailIsShown: false,
            isEditMode: false,
        });
        this.intFields = ['country_id', 'state_id', 'property_product_pricelist'];
        this.changes = {};
        this.updateClientList = debounce(this.updateClientList, 70);
    }

    // Lifecycle hooks
    back() {
        if (this.state.detailIsShown) {
            this.state.detailIsShown = false;
        } else {
            this.props.resolve([false]);
            this.trigger('close-temp-screen');
        }
    }
    confirm() {
        this.props.resolve([true, this.state.selectedClientId]);
        this.trigger('close-temp-screen');
    }
    // Getters

    getVisibleClients() {
        const query = this.state.query.trim();
        return this.env.model.getPartners(query);
    }
    get isNextButtonVisible() {
        return this.state.selectedClientId ? true : false;
    }
    /**
     * Returns the text and command of the next button.
     * The command field is used by the clickNext call.
     */
    get nextButton() {
        if (!this.props.clientId) {
            return { command: 'set', text: 'Set Customer' };
        } else if (this.props.clientId && this.props.clientId === this.state.selectedClientId) {
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
        if (event.code === 'Enter') {
            const visibleClients = this.getVisibleClients();
            if (visibleClients.length !== 1) return;
            this.state.selectedClientId = visibleClients[0].id;
            this.clickNext();
        }
    }
    onClickClient(partner) {
        let partnerId = partner.id;
        if (this.state.selectedClientId === partnerId) {
            this.state.selectedClientId = null;
        } else {
            this.state.selectedClientId = partnerId;
        }
    }
    onClickEdit() {
        this.state.detailIsShown = true;
    }
    clickNext() {
        this.state.selectedClientId = this.nextButton.command === 'set' ? this.state.selectedClientId : null;
        this.confirm();
    }
    onCreateNewClient() {
        this.state.isEditMode = true;
        this.state.detailIsShown = true;
        this.state.isNewClient = true;
    }
    deactivateEditMode() {
        this.state.isEditMode = false;
    }
    async onClickSave() {
        const processedChanges = {};
        for (let [key, value] of Object.entries(this.changes)) {
            if (this.intFields.includes(key)) {
                processedChanges[key] = parseInt(value) || false;
            } else {
                processedChanges[key] = value;
            }
        }
        if (processedChanges.name === '') {
            return this.showPopup('ErrorPopup', {
                title: _('A Customer Name Is Required'),
            });
        }
        processedChanges.id = this.state.selectedClientId || false;
        try {
            let partnerId = await this.uirpc({
                model: 'res.partner',
                method: 'create_from_ui',
                args: [processedChanges],
            });
            await this.env.model.actionHandler({ name: 'actionLoadUpdatedPartners' });
            this.state.selectedClientId = partnerId;
            this.state.detailIsShown = false;
        } catch (error) {
            if (error.message.code < 0) {
                await this.showPopup('OfflineErrorPopup', {
                    title: this.env._t('Offline'),
                    body: this.env._t('Unable to save changes.'),
                });
            } else {
                throw error;
            }
        }
        this.changes = {};
    }
    isHighlighted(customer) {
        return this.state.selectedClientId ? customer.id === this.state.selectedClientId : false;
    }
    get partnerImageUrl() {
        // We prioritize image_1920 in the `changes` field because we want
        // to show the uploaded image without fetching new data from the server.
        const partner = this.state.selectedClientId;
        if (this.changes.image_1920) {
            return this.changes.image_1920;
        } else if (partner.id) {
            return `/web/image?model=res.partner&id=${partner.id}&field=image_128&write_date=${partner.write_date}&unique=1`;
        } else {
            return false;
        }
    }
    getClientToEdit() {
        return this.state.selectedClientId
            ? this.env.model.getRecord('res.partner', this.state.selectedClientId)
            : {
                  country_id: this.env.model.company.country_id,
                  state_id: this.env.model.company.state_id,
              };
    }
    /**
     * Save to field `changes` all input changes from the form fields.
     */
    captureChange(event) {
        this.changes[event.target.name] = event.target.value;
    }
    async uploadImage(event) {
        const file = event.target.files[0];
        if (!file.type.match(/image.*/)) {
            await this.showPopup('ErrorPopup', {
                title: this.env._t('Unsupported File Format'),
                body: this.env._t('Only web-compatible Image formats such as .png or .jpeg are supported.'),
            });
        } else {
            const imageUrl = await getDataURLFromFile(file);
            const loadedImage = await this._loadImage(imageUrl);
            if (loadedImage) {
                const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                this.changes.image_1920 = resizedImage.toDataURL();
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
     * loading an image. It resolves to the loaded image if succesful,
     * else, resolves to false.
     *
     * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
     */
    _loadImage(url) {
        return new Promise((resolve) => {
            const img = new Image();
            img.addEventListener('load', () => resolve(img));
            img.addEventListener('error', () => {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Loading Image Error'),
                    body: this.env._t('Encountered error when loading image. Please try again.'),
                });
                resolve(false);
            });
            img.src = url;
        });
    }
}
ClientListScreen.template = 'point_of_sale.ClientListScreen';

export default ClientListScreen;
