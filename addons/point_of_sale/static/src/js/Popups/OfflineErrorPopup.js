odoo.define('point_of_sale.OfflineErrorPopup', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');
    const { Gui } = require('point_of_sale.Gui');

    /**
     * This is a special kind of error popup: we want to display it only once, because otherwise it creates
     * a negative UX. Instead of throwing errors at the user, we remind them that some actions are unavailable
     * during the offline mode by keeping the sync status icon (top right corner of the UI) always up to date
     * and by displaying a toast notification.
     */
    class OfflineErrorPopup extends ErrorPopup {
        setup() {
            super.setup();
            if (!this.constructor.shouldShow) {
                Gui.showNotification(this.props.body, 3000);
                this.cancel();
            } else {
                this.constructor.shouldShow = false;
                this.startPolling();
            }
            owl.onWillUnmount(() => this.env.pos.set_synch('disconnected'));
        }
        startPolling() {
            this.constructor.pollingIntervalId = setInterval(async () => {
                const isConnectionOk = await this.pingServer();
                const newStatus = isConnectionOk ? 'connected' : 'disconnected';
                this.updateSyncStatus(newStatus);
                if (isConnectionOk) this.stopPolling();
            }, 30000);
        }
        stopPolling() {
            clearInterval(this.constructor.pollingIntervalId);
            this.constructor.pollingIntervalId = false;
            this.constructor.shouldShow = true;
        }
        updateSyncStatus(newStatus) {
            this.env.pos.set_synch('connecting');
            // delay 2 sec so that the 'connecting' phase is visible to the user
            setTimeout(() => this.env.pos.set_synch(newStatus), 2000);
        }
        async pingServer() {
            try {
                await this.env.services.rpc({
                    route: '/web/webclient/version_info'
                });
                return true;
            } catch {
                return false;
            }
        }
    }
    OfflineErrorPopup.template = 'OfflineErrorPopup';
    OfflineErrorPopup.shouldShow = true;
    OfflineErrorPopup.pollingIntervalId = false;
    OfflineErrorPopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: _lt('Offline Error'),
        body: _lt('Either the server is inaccessible or browser is not connected online.'),
    };

    Registries.Component.add(OfflineErrorPopup);

    return OfflineErrorPopup;
});
