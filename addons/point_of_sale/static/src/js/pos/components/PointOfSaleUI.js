/** @odoo-module alias=point_of_sale.PointOfSaleUI **/

import { loadCSS } from 'web.ajax';
import { useListener } from 'web.custom_hooks';
import { CrashManager } from 'web.CrashManager';
import { BarcodeEvents } from 'barcodes.BarcodeEvents';
import PosComponent from 'point_of_sale.PosComponent';
import TicketButton from 'point_of_sale.TicketButton';
import HeaderButton from 'point_of_sale.HeaderButton';
import CashierName from 'point_of_sale.CashierName';
import ProxyStatus from 'point_of_sale.ProxyStatus';
import SyncNotification from 'point_of_sale.SyncNotification';
import ClientScreenButton from 'point_of_sale.ClientScreenButton';
import SaleDetailsButton from 'point_of_sale.SaleDetailsButton';
import OrderManagementButton from 'point_of_sale.OrderManagementButton';
import NumberBuffer from 'point_of_sale.NumberBuffer';
import ProductScreen from 'point_of_sale.ProductScreen';
import TicketScreen from 'point_of_sale.TicketScreen';
import ClientListScreen from 'point_of_sale.ClientListScreen';
import PaymentScreen from 'point_of_sale.PaymentScreen';
import ReceiptScreen from 'point_of_sale.ReceiptScreen';
import OrderManagementScreen from 'point_of_sale.OrderManagementScreen';
import ReprintReceiptScreen from 'point_of_sale.ReprintReceiptScreen';
import ScaleScreen from 'point_of_sale.ScaleScreen';
import BasicSearchBar from 'point_of_sale.BasicSearchBar';
import PosDialog from 'point_of_sale.PosDialog';
import Notification from 'point_of_sale.Notification';
import NotificationSound from 'point_of_sale.NotificationSound';
import DebugWidget from 'point_of_sale.DebugWidget';

class PointOfSaleUI extends PosComponent {
    constructor() {
        super(...arguments);
        this.basicSearchBarRef = owl.hooks.useRef('basic-search-bar');
        this.syncNotificationRef = owl.hooks.useRef('sync-notification-ref');
        this.posDialogRef = owl.hooks.useRef('pos-dialog-ref');
        this.toastNotificationRef = owl.hooks.useRef('toast-notification-ref');
        this.notificationSoundRef = owl.hooks.useRef('notification-sound-ref');
        owl.hooks.useExternalListener(window, 'storage', this._closeOtherTabs);
        useListener('toggle-debug-widget', () => {
            this.state.debugWidgetIsShown = !this.state.debugWidgetIsShown;
        });
        useListener('click-sync-notification', this._onClickSyncNotification);
        useListener('show-temp-screen', this.__showTempScreen);
        useListener('close-temp-screen', this.__closeTempScreen);
        this.state = owl.useState({ tempScreenName: false, debugWidgetIsShown: true });
        this._tempScreenProps = {};
        NumberBuffer.activate();
        this.env.model.useModel();
    }
    mounted() {
        // remove default webclient handlers that induce click delay
        $(document).off();
        $(window).off();
        $('html').off();
        $('body').off();
        // The above lines removed the bindings, but we really need them for the barcode
        BarcodeEvents.start();
        this._buildChrome();
        this._disableBackspaceBack();
        this._replaceCrashmanager();
        this._loadPos();
    }
    willUnmount() {
        BarcodeEvents.stop();
    }
    async _onClickSyncNotification() {
        await this.env.model.actionHandler({ name: 'actionSyncOrders' });
    }
    getMainScreen() {
        const activeScreen = this.env.model.getActiveScreen();
        const activeScreenProps = this.env.model.getActiveScreenProps();
        return {
            name: activeScreen,
            component: this.constructor.components[activeScreen],
            props: activeScreenProps,
        };
    }
    getTempScreen() {
        const name = this.state.tempScreenName;
        if (!name) return false;
        return {
            name,
            component: this.constructor.components[name],
            props: this._tempScreenProps,
        };
    }
    getSyncNotificationMsg() {
        return this.env.model.getOrdersToSync().length;
    }
    showClientScreenButton() {
        return (
            (this.env.model.config.is_posbox && this.env.model.config.iface_customer_facing_display_via_proxy) ||
            this.env.model.config.iface_customer_facing_display_local
        );
    }
    __showTempScreen({ detail: { name, props, resolve } }) {
        this.state.tempScreenName = name;
        Object.assign(this._tempScreenProps, props, { resolve });
    }
    __closeTempScreen() {
        this.state.tempScreenName = false;
        Object.assign(this._tempScreenProps, {});
    }
    /**
     * This method is called when this component is properly mounted.
     */
    async _loadPos() {
        try {
            await this.env.model.loadPosData();
            // Trigger storage event to close pos from other open tabs.
            // See _closeOtherTabs.
            localStorage['message'] = '';
            localStorage['message'] = JSON.stringify({
                message: 'close_tabs',
                session: this.env.model.session.id,
            });
        } catch (error) {
            console.error(error);
            let title = this.env._t('Unknown Error');
            let body;
            if (error.message && [100, 200, 404, -32098].includes(error.message.code)) {
                // this is the signature of rpc error
                if (error.message.code === -32098) {
                    title = this.env._t('Network Failure (XmlHttpRequestError)');
                    body = this.env._t(
                        'The Point of Sale could not be loaded due to a network problem.\n' +
                            'Please check your internet connection.'
                    );
                } else if (error.message.code === 200) {
                    title = error.message.data.message || this.env._t('Server Error');
                    body =
                        error.message.data.debug ||
                        this.env._t('The server encountered an error while receiving your order.');
                }
            } else if (error instanceof Error) {
                title = error.message;
                body = error.stack;
            }
            await this.env.ui.askUser('ErrorTracebackPopup', {
                title,
                body,
                exitButtonIsShown: true,
            });
        }
    }
    async stopSearching() {
        await this.env.model.proxy.stop_searching();
    }

    //#region MISC

    _buildChrome() {
        if ($.browser.chrome) {
            var chrome_version = $.browser.version.split('.')[0];
            if (parseInt(chrome_version, 10) >= 50) {
                loadCSS('/point_of_sale/static/src/css/chrome50.css');
            }
        }
    }
    /**
     * Use pos popup to show detected crashes.
     */
    _replaceCrashmanager() {
        const self = this;
        CrashManager.include({
            show_error: function (error) {
                if (self.env) {
                    // self == this component
                    self.env.ui.askUser('ErrorTracebackPopup', {
                        title: error.type,
                        body: error.message + '\n' + error.data.debug + '\n',
                    });
                } else {
                    // this == CrashManager instance
                    this._super(error);
                }
            },
        });
    }
    /**
     * NOTE: Doesn't seem to be needed. But to be sure, just do it anyway.
     */
    _disableBackspaceBack() {
        $(document).on('keydown', function (e) {
            if (e.which === 8 && !$(e.target).is('input, textarea')) {
                e.preventDefault();
            }
        });
    }
    _closeOtherTabs(event) {
        if (event.key === 'message' && event.newValue) {
            const msg = JSON.parse(event.newValue);
            if (msg.message === 'close_tabs' && msg.session == this.env.model.session.id) {
                console.info('POS / Session opened in another window. EXITING POS');
                this.env.model.actionHandler({ name: 'actionClosePos' });
            }
        }
    }

    //#endregion
}
PointOfSaleUI.components = {
    TicketButton,
    HeaderButton,
    CashierName,
    ProxyStatus,
    SyncNotification,
    ClientScreenButton,
    SaleDetailsButton,
    OrderManagementButton,
    ProductScreen,
    TicketScreen,
    ClientListScreen,
    PaymentScreen,
    ReceiptScreen,
    ReprintReceiptScreen,
    OrderManagementScreen,
    ScaleScreen,
    BasicSearchBar,
    PosDialog,
    Notification,
    NotificationSound,
    DebugWidget,
};
PointOfSaleUI.template = 'point_of_sale.PointOfSaleUI';

export default PointOfSaleUI;
