import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import { formatDate } from '@web/core/l10n/dates';

const { DateTime } = luxon;

export class DeliveryDatePicker extends Interaction {
    static selector = '.o_website_sale_delivery_date_picker';

    start() {
        const deliveryMethod = this.el.closest('li[name="o_delivery_method"]');
        this.deliveryRadio = deliveryMethod.querySelector('input[name="o_delivery_radio"]');
        this.availableDays = JSON.parse(this.el.dataset.deliveryAvailableDays);
        const locale = document.documentElement.getAttribute('lang') || 'en-US';
        const defaultDate = DateTime.fromISO(this.availableDays[0], { locale });
        const lastDate = DateTime.fromISO(this.availableDays[this.availableDays.length - 1]);
        this.registerCleanup(
            this.services.datetime_picker.create(
                {
                    target: this.el,
                    format: 'MMM d, yyyy',
                    pickerProps: {
                        value: defaultDate,
                        type: 'date',
                        minDate: defaultDate,
                        maxDate: lastDate,
                        isDateValid: this._isDateValid.bind(this),
                    },
                    onChange: () => {
                        // Make sure that the delivery method we're modifying is the selected one
                        this.deliveryRadio.click();
                    },
                    onApply: async (deliveryDate) => {
                        await this.waitFor(rpc('/website_sale/set_delivery_date', {
                            delivery_date: formatDate(deliveryDate, { format: 'yyyy-MM-dd' }),
                        }));
                    },
                    getInputs: () => [
                        this.el.querySelector('input[name=estimated_delivery]'),
                    ],
                },
            ).enable()
        );
    }

    /**
    * Check if the date is valid.
    *
    * This function is used in the daterange picker objects and meant to be easily overriden.
    *
    * @param {DateTime} date
    * @private
    */
    _isDateValid(date) {
        return this.availableDays.includes(date.toISODate());
    }
}

registry
    .category('public.interactions')
    .add('website_sale.daterange_picker', DeliveryDatePicker);
