import { proxy, usePlugin, Plugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { PosDataPlugin } from "./pos_data_plugin";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectDefaultPaymentMethodPopup } from "@point_of_sale/app/components/popups/select_default_payment_method_popup/select_default_payment_method_popup";

export class PosPaymentMethodPlugin extends Plugin {
    // After PosDataPlugin (20)
    static sequence = 30;

    data = usePlugin(PosDataPlugin);
    dialog = usePlugin(DialogPlugin);

    setup() {
        this.defaultGroups = {};
        this.defaultIds = proxy({});
    }

    get config() {
        return this.data.models["pos.config"].get(odoo.pos_config_id);
    }

    // Called once the data is loaded, the payment interfaces need the pos store
    init(pos) {
        this.initPaymentInterfaces(pos);
        this.initDefaults();
    }

    initPaymentInterfaces(pos) {
        for (const pm of this.config.payment_method_ids) {
            const PaymentInterface = registry
                .category("pos_payment_providers")
                .get(pm.payment_provider, null);
            pm.payment_interface = PaymentInterface ? new PaymentInterface(pos, pm) : null;
        }
    }

    initDefaults() {
        this.defaultGroups = this.computeDefaultGroups();
        for (const provider of Object.keys(this.defaultGroups)) {
            const key = this.getDefaultStorageKey(provider);
            this.defaultIds[provider] = Number(localStorage.getItem(key)) || false;
        }
    }

    computeDefaultGroups() {
        const groups = {};
        for (const pm of this.config.paymentMethods) {
            if (pm.payment_interface) {
                (groups[pm.payment_provider] ||= []).push(pm);
            }
        }
        return Object.fromEntries(Object.entries(groups).filter(([, pms]) => pms.length > 1));
    }

    getDefaultStorageKey(provider) {
        return `pos_default_payment_method_id_${provider}_${this.config.id}_${odoo.info?.db}`;
    }

    getDefault(provider) {
        const pmId = this.defaultIds[provider];
        return this.defaultGroups[provider]?.find((pm) => pm.id === pmId);
    }

    setDefault(provider, pmId) {
        const key = this.getDefaultStorageKey(provider);
        if (pmId) {
            localStorage.setItem(key, pmId);
        } else {
            localStorage.removeItem(key);
        }
        this.defaultIds[provider] = pmId || false;
    }

    async selectDefaults(providers = Object.keys(this.defaultGroups)) {
        const selection = await makeAwaitable(this.dialog, SelectDefaultPaymentMethodPopup, {
            groups: providers.map((provider) => ({
                provider,
                name: this.defaultGroups[provider][0]._payment_provider_name,
                paymentMethods: this.defaultGroups[provider],
                selectedId: this.getDefault(provider)?.id || false,
            })),
        });
        if (!selection) {
            return false;
        }
        for (const [provider, pmId] of Object.entries(selection)) {
            this.setDefault(provider, pmId);
        }
        return true;
    }
}
