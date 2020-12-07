/** @odoo-module alias=point_of_sale.ProxyStatus **/

const { useState } = owl;
import PosComponent from 'point_of_sale.PosComponent';

class ProxyStatus extends PosComponent {
    constructor() {
        super(...arguments);
        const initialProxyStatus = this.env.model.proxy.get('status');
        this.state = useState({
            status: initialProxyStatus.status,
            msg: initialProxyStatus.msg,
        });
        this.statuses = ['connected', 'connecting', 'disconnected', 'warning'];
        this.index = 0;
    }
    mounted() {
        this.env.model.proxy.on('change:status', this, this._onChangeStatus);
    }
    willUnmount() {
        this.env.model.proxy.off('change:status', this, this._onChangeStatus);
    }
    async onClick() {
        try {
            await this.env.model.actionHandler({ name: 'actionConnectToProxy' });
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            } else {
                this.env.ui.askUser('ErrorPopup', error);
            }
        }
    }
    _onChangeStatus(posProxy, statusChange) {
        this._setStatus(statusChange.newValue);
    }
    _setStatus(newStatus) {
        if (newStatus.status === 'connected') {
            var warning = false;
            var msg = '';
            if (this.env.model.config.iface_scan_via_proxy) {
                var scannerStatus = newStatus.drivers.scanner ? newStatus.drivers.scanner.status : false;
                if (scannerStatus != 'connected' && scannerStatus != 'connecting') {
                    warning = true;
                    msg += this.env._t('Scanner');
                }
            }
            if (this.env.model.config.iface_print_via_proxy || this.env.model.config.iface_cashdrawer) {
                var printerStatus = newStatus.drivers.printer ? newStatus.drivers.printer.status : false;
                if (printerStatus != 'connected' && printerStatus != 'connecting') {
                    warning = true;
                    msg = msg ? msg + ' & ' : msg;
                    msg += this.env._t('Printer');
                }
            }
            if (this.env.model.config.iface_electronic_scale) {
                var scaleStatus = newStatus.drivers.scale ? newStatus.drivers.scale.status : false;
                if (scaleStatus != 'connected' && scaleStatus != 'connecting') {
                    warning = true;
                    msg = msg ? msg + ' & ' : msg;
                    msg += this.env._t('Scale');
                }
            }
            msg = msg ? msg + ' ' + this.env._t('Offline') : msg;

            this.state.status = warning ? 'warning' : 'connected';
            this.state.msg = msg;
        } else {
            this.state.status = newStatus.status;
            this.state.msg = newStatus.msg || '';
        }
    }
}
ProxyStatus.template = 'point_of_sale.ProxyStatus';

export default ProxyStatus;
