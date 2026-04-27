import { patch } from "@web/core/utils/patch";
import { PosStore, register_payment_method } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { DeviceController } from "@iot/device_controller";
import { IoTPrinter } from "@pos_iot/app/iot_printer";
import { PaymentIngenico, PaymentWorldline } from "@pos_iot/app/payment";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.env.services.iot_longpolling.setLna(odoo.use_lna);
    },
    async processServerData(loadedData) {
        await super.processServerData(...arguments);

        this._loadIotDevice(this.models["iot.device"].getAll());
        this.hardwareProxy.iotBoxes = this.models["iot.box"].getAll();
    },
    _loadIotDevice(devices) {
        const iotLongpolling = this.env.services.iot_longpolling;
        for (const device of devices) {
            // FIXME POSREF this seems like it can't work, we're pushing an id to an array of
            // objects expected to be of the form { ip, ip_url }, so this seems useless?
            if (!this.hardwareProxy.iotBoxes.includes(device.iot_id.id)) {
                this.hardwareProxy.iotBoxes.push(device.iot_id.id);
            }
            const { deviceControllers } = this.hardwareProxy;
            const { type, identifier } = device;
            const deviceProxy = new DeviceController(iotLongpolling, device);
            if (type === "payment") {
                for (const pm of this.models["pos.payment.method"].getAll()) {
                    if (pm.iot_device_id?.id === device.id) {
                        pm.terminal_proxy = deviceProxy;
                    }
                }
            } else if (type === "scanner") {
                deviceControllers.scanners ||= {};
                deviceControllers.scanners[identifier] = deviceProxy;
            } else {
                deviceControllers[type] = deviceProxy;
            }
        }
    },
    create_printer(config) {
        if (config.device_identifier && config.printer_type === "iot") {
            const device = new DeviceController(this.env.services.iot_longpolling, {
                iot_ip: config.proxy_ip,
                identifier: config.device_identifier,
            });
            return new IoTPrinter({ device });
        } else {
            return super.create_printer(...arguments);
        }
    },

    showScreen(name, props) {
        if (
            this.mainScreen.component === PaymentScreen &&
            this.get_order().payment_ids.some(
                (pl) =>
                    pl.payment_method_id.use_payment_terminal === "worldline" &&
                    ["waiting", "waitingCard", "waitingCancel"].includes(pl.payment_status)
            )
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Transaction in progress"),
                body: _t("Please process or cancel the current transaction."),
            });
        } else {
            return super.showScreen(...arguments);
        }
    },
    useProxy() {
        return (
            super.useProxy() ||
            (this.config.iot_device_ids && this.config.iot_device_ids.length > 0)
        );
    },
    connectToProxy() {
        this.hardwareProxy.pingBoxes();
        if (this.config.iface_scan_via_proxy) {
            this.barcodeReader?.connectToProxy();
        }
        if (this.config.iface_print_via_proxy) {
            this.hardwareProxy.connectToPrinter();
        }
        if (!this.hardwareProxy.statusLoopRunning) {
            this.hardwareProxy.statusLoop();
        }
        return Promise.resolve();
    },

    getDisplayDeviceIP() {
        if (this.config.iface_display_id) {
            return this.config.iface_display_id.iot_ip;
        } else {
            return super.getDisplayDeviceIP();
        }
    },
});

register_payment_method("ingenico", PaymentIngenico);
register_payment_method("worldline", PaymentWorldline);
