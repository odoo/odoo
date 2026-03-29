/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { PaymentScreen } from '@point_of_sale/app/screens/payment_screen/payment_screen';
import { patch } from '@web/core/utils/patch';
import { Component, onWillUnmount } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { register_payment_method } from '@point_of_sale/app/store/pos_store';
import { PaymentInterface } from '@point_of_sale/app/payment/payment_interface';

// ============================================================
// Dialog: en attente de confirmation du terminal Bictorys
// ============================================================

class BictorysPaymentDialog extends Component {
    static template = 'payment_bictorys.BictorysPaymentDialog';
    static components = { Dialog };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.notification = useService('notification');

        // Polling toutes les 2 secondes — le webhook serveur met à jour bictorys_payment_status
        this._interval = setInterval(() => this._poll(), 2000);
        onWillUnmount(() => clearInterval(this._interval));
    }

    async _poll() {
        try {
            const status = await this.orm.call(
                'pos.order',
                'bictorys_get_order_status',
                [this.props.posReference],
            );
            console.log('[Bictorys] poll status:', status);
            if (status === 'succeeded') {
                clearInterval(this._interval);
                this.props.close();
                this.props.onSuccess();
            } else if (status === 'failed') {
                clearInterval(this._interval);
                this.props.close();
                this.props.onFailure();
            }
        } catch (e) {
            console.error('[Bictorys] poll error:', e);
        }
    }

    async onCancel() {
        clearInterval(this._interval);
        try {
            await this.orm.call('pos.order', 'bictorys_cancel_order', [this.props.posReference]);
        } catch (e) {
            console.error('[Bictorys] cancel error:', e);
        }
        this.props.close();
        this.props.onFailure();
    }
}

// ============================================================
// Dialog: erreur création commande Bictorys
// ============================================================

class BictorysErrorDialog extends Component {
    static template = 'payment_bictorys.BictorysErrorDialog';
    static components = { Dialog };
    setup() { super.setup(); }
    onClose() { this.props.close(); }
}

// ============================================================
// PATCH PaymentScreen
//
// 1. _isOrderValid: masque is_online_payment pendant la validation
//    Bictorys pour bloquer le QR code natif de pos_online_payment.
//
// 2. afterOrderValidation: après que sync_from_ui a tourné côté
//    serveur (et créé la commande Bictorys), on ouvre le dialog
//    de polling.
// ============================================================

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._bictorysDialog = useService('dialog');
        this._bictorysOrm = useService('orm');
    },

    _hasBictorysPayment() {
        return this.currentOrder?.payment_ids?.some(
            (p) => p.payment_method_id?.use_payment_terminal === 'bictorys'
        );
    },

    // Bloque le flux QR natif de pos_online_payment pour les paiements Bictorys.
    async _isOrderValid(isForceValidate) {
        if (!this._hasBictorysPayment()) {
            return super._isOrderValid(...arguments);
        }

        const maskedMethods = this.payment_methods_from_config?.filter(
            (pm) => pm.is_online_payment
        ) || [];

        console.log('[Bictorys] _isOrderValid — masking', maskedMethods.length, 'online methods');
        for (const pm of maskedMethods) pm.is_online_payment = false;

        let result;
        try {
            result = await super._isOrderValid(...arguments);
        } finally {
            for (const pm of maskedMethods) pm.is_online_payment = true;
        }
        console.log('[Bictorys] _isOrderValid result:', result);
        return result;
    },

    // Appelé après que Odoo a finalisé la commande et appelé sync_from_ui.
    // À ce stade, le serveur a créé la commande sur Bictorys via sync_from_ui.
    async afterOrderValidation(retry = false) {
        if (!this._hasBictorysPayment()) {
            return super.afterOrderValidation(retry);
        }

        const order = this.currentOrder;
        const posReference = order.pos_reference;
        const nextScreen = this.nextScreen;
        const self = this;

        let result;
        try {
            result = await this._bictorysOrm.call(
                'pos.order',
                'bictorys_check_after_validation',
                [posReference],
            );
        } catch (e) {
            console.error('[Bictorys] check error:', e);
            this._bictorysDialog.add(BictorysErrorDialog, {
                message: _t("Erreur serveur lors de la vérification Bictorys."),
            });
            return;
        }

        console.log('[Bictorys] check result:', result);

        if (!result || result.status !== 'ok') {
            this._bictorysDialog.add(BictorysErrorDialog, {
                message: _t(
                    "La commande n'a pas pu être envoyée au terminal Bictorys. "
                    + "Vérifiez la configuration et réessayez."
                ),
            });
            return;
        }

        // Ouvrir le dialog de polling
        this._bictorysDialog.add(BictorysPaymentDialog, {
            posReference,
            bictorysOrderId: result.bictorys_order_id,
            message: _t(
                'En attente de confirmation du paiement Bictorys pour la commande %s...',
                order.name,
            ),
            onSuccess: () => self.pos.showScreen(nextScreen),
            onFailure: () => self.pos.showScreen('ProductScreen'),
        });
    }
});

// ============================================================
// PaymentBictorys — requis pour que register_payment_method
// fonctionne (use_payment_terminal = 'bictorys').
// Le flux réel est géré par afterOrderValidation + sync_from_ui.
// ============================================================

class PaymentBictorys extends PaymentInterface {
    send_payment_request(uuid) {
        super.send_payment_request(uuid);
        // Rien à faire ici — sync_from_ui côté serveur crée la commande Bictorys.
        // afterOrderValidation s'occupera du dialog de suivi.
        return Promise.resolve(true);
    }
    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        return Promise.resolve(true);
    }
}

register_payment_method('bictorys', PaymentBictorys);