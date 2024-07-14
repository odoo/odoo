/** @odoo-module **/

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from '@web/core/l10n/translation';
import { renderToMarkup } from '@web/core/utils/render';

import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    /**
     * Replace the base token deletion confirmation dialog to prevent token deletion if a linked
     * subscription is active.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} tokenId - The id of the token whose deletion was requested.
     * @param {object} linkedRecordsInfo - The data relative to the documents linked to the token.
     * @return {void}
     */
    _challengeTokenDeletion(tokenId, linkedRecordsInfo) {
        if (linkedRecordsInfo.every(linkedRecordInfo => !linkedRecordInfo['active_subscription'])) {
            this._super(...arguments);
            return;
        }

        const body = renderToMarkup('sale_subscription.deleteTokenDialog', { linkedRecordsInfo });
        this.call('dialog', 'add', ConfirmationDialog, {
            title: _t("Warning!"),
            body,
            cancel: () => {},
        });
    },

});
