import publicWidget from '@web/legacy/js/public/public_widget';
import { browser } from '@web/core/browser/browser';

publicWidget.registry.PaymentInstallments = publicWidget.Widget.extend({
    selector: '#o_payment_installments_modal',

    /**
     * @override
     */
    async start() {

        await this._super(...arguments);
        this._onChangePaymentTabs();

    },

    /**
     * Handles payment tab changes (installment or full amount).
     *
     * This method listens for the `shown.bs.tab` event on payment tab buttons.
     * When the user switches tabs, it updates the URL parameters `mode` and
     * `render_change`, then reloads the page. This forces the backend to
     * re-render the payment form with updated data, including the corresponding
     * amount and available payment providers.
     *
     * Added URL parameters:
     * - mode: either 'installment' or 'full', depending on the selected tab.
     * - render_change: 'true', indicating that the change should trigger a re-render.
     */
    _onChangePaymentTabs() {
        $('.o_btn_payment_tab').on('shown.bs.tab', function (event) {
            const activatedTab = event.target.id;
            const mode = activatedTab === 'o_payment_installments_tab'
                ? 'installment'
                : (activatedTab === 'o_payment_full_tab' ? 'full' : null);

            if (mode) {
                const url = new URL(window.location.href, location.origin);
                url.searchParams.set('mode', encodeURIComponent(mode));
                url.searchParams.set('render_change', 'true');
                document.location = encodeURI(url.href);
            }
        });
    }

})

export default publicWidget.registry.PaymentInstallments;