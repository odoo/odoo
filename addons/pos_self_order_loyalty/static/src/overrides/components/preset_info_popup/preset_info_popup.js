import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { IdentifyBanner } from "@pos_self_order_loyalty/app/components/identify_banner/identify_banner";

const { DateTime } = luxon;

/**
 * A customer who identified stays the order's customer, with their loyalty: they pick one of
 * their addresses, or add one, as the order's delivery address (delivery_partner_id).
 */
patch(PresetInfoPopup.prototype, {
    setup() {
        super.setup();
        Object.assign(this.state, {
            addresses: [], // plain data, only the chosen one is added to the models
            selectedAddressId: null,
            addressToArchiveId: null, // waiting for the customer's confirmation
            showAddressForm: false,
        });
        const partner = this.identifiedCustomer;
        if (partner && partner.name === partner.email) {
            this.state.name = ""; // named after their email when identified by it
        }
        onWillStart(async () => {
            if (this.identifiedCustomer) {
                await this.loadAddresses();
            }
        });
    },

    /** The identified customer, when the order is theirs and needs an address. */
    get identifiedCustomer() {
        const partner = this.selfOrder.identifiedPartner;
        return this.preset?.needsPartner &&
            partner &&
            this.selfOrder.currentOrder.partner_id === partner
            ? partner
            : null;
    },

    async loadAddresses() {
        try {
            const result = await rpc("/pos-self-order/get-delivery-addresses", {
                access_token: this.selfOrder.access_token,
                partner_id: this.identifiedCustomer.id,
            });
            this.state.addresses = result["res.partner"];
        } catch {
            this.state.addresses = []; // the customer can still enter an address
        }
        this.state.selectedAddressId = this.state.addresses[0]?.id || null;
        this.state.showAddressForm = !this.state.addresses.length;
    },

    formatAddress(address) {
        const country = this.selfOrder.models["res.country"].get(address.country_id);
        return [
            address.street,
            [address.zip, address.city].filter(Boolean).join(" "),
            country?.name,
        ]
            .filter(Boolean)
            .join(", ");
    },

    selectAddress(address) {
        this.state.selectedAddressId = address.id;
        this.state.validationError = null;
    },

    showNewAddressForm() {
        Object.assign(this.state, { street: "", city: "", zip: "", validationError: null });
        this.state.showAddressForm = true;
    },

    showAddresses() {
        this.state.showAddressForm = false;
        this.state.validationError = null;
    },

    askArchiveAddress(address) {
        this.state.addressToArchiveId = address.id;
    },

    cancelArchiveAddress() {
        this.state.addressToArchiveId = null;
    },

    async archiveAddress(address) {
        this.state.addressToArchiveId = null;
        try {
            await rpc("/pos-self-order/archive-delivery-address", {
                access_token: this.selfOrder.access_token,
                partner_id: this.identifiedCustomer.id,
                delivery_partner_id: address.id,
            });
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            return;
        }
        this.state.addresses = this.state.addresses.filter((a) => a.id !== address.id);
        if (this.state.selectedAddressId === address.id) {
            this.state.selectedAddressId = this.state.addresses[0]?.id || null;
        }
        this.state.showAddressForm = !this.state.addresses.length;
    },

    get validSelection() {
        if (!this.identifiedCustomer || this.state.showAddressForm) {
            return super.validSelection;
        }
        const time = this.selfOrder.currentOrder.raw.preset_time;
        return (
            Boolean(this.state.selectedAddressId) &&
            (!this.preset.needsSlot || DateTime.fromSQL(time).isValid)
        );
    },

    async setInformations() {
        const partner = this.identifiedCustomer;
        if (!partner) {
            return super.setInformations();
        }
        if (this.state.isSubmitting || (this.state.showAddressForm && !this.checkPhoneFormat())) {
            return;
        }
        this.state.isSubmitting = true;
        this.state.validationError = null;
        try {
            const addressValues = this.state.showAddressForm
                ? {
                      name: this.state.name,
                      phone: this.getFullPhone(),
                      street: this.state.street,
                      city: this.state.city,
                      country_id: this.state.countryId,
                      state_id: this.state.stateId,
                      zip: this.state.zip,
                  }
                : { delivery_partner_id: this.state.selectedAddressId };
            const result = await rpc("/pos-self-order/validate-partner", {
                access_token: this.selfOrder.access_token,
                preset_id: this.preset.id,
                partner_id: partner.id,
                ...addressValues,
            });
            if (this.handleValidationErrors(result)) {
                return;
            }
            const data = { "res.partner": result["res.partner"] };
            const [address] = this.selfOrder.models.connectNewData(data)["res.partner"];
            this.selfOrder.data.synchronizeServerDataInIndexedDB(data);
            const order = this.selfOrder.currentOrder;
            order.delivery_partner_id = address;
            order.floating_order_name = `${this.preset.name} - ${address.name || partner.name}`;
            this.props.getPayload({ ...this.state, phone: address.phone || partner.phone || "" });
            this.props.close();
        } finally {
            this.state.isSubmitting = false;
        }
    },
});

patch(PresetInfoPopup, {
    components: { ...PresetInfoPopup.components, IdentifyBanner },
});
