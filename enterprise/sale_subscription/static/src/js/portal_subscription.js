/** @odoo-module **/

    import publicWidget from "@web/legacy/js/public/public_widget";

    publicWidget.registry.SubscriptionChangePlan = publicWidget.Widget.extend({
        selector: '.o_portal_sale_sidebar',

        start: async function () {
            if (new URLSearchParams(window.location.search).get('change_plan') === 'true') {
                const changePlanButton = document.getElementById('o_change_plan');
                changePlanButton && changePlanButton.click();
            }
        }
    });

    publicWidget.registry.SubscriptionCloseSelect = publicWidget.Widget.extend({
        selector: '#subscription-close-select',
        events: {
            'change': '_onChange',
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _onChange: function () {
            const reasonId = this.$el.val();
            const messages = document.querySelectorAll('.subscription-close-message, .subscription-close-link');
            const retainButton = document.querySelector('.subscription-close-init-retain');
            const noRetainButton = document.querySelector('.subscription-close-init-noretain');
            const tooltipWrapper = document.querySelector('.tooltip-wrapper');

            messages.forEach(message => {
                message.style.display = (message.dataset.id === reasonId) ? 'block' : 'none';
            });

            // Reset button visibility and tooltip
            retainButton.classList.add('d-none');
            noRetainButton.classList.add('disabled');
            noRetainButton.classList.remove('d-none');
            tooltipWrapper.dataset.tooltip = 'Choose a closing reason before submitting';

            if (reasonId) {
                const selectedOption = this.$el.find(':selected');
                const hasRetention = selectedOption?.data('retention');
                if (hasRetention) {
                    retainButton.classList.remove('d-none');
                    noRetainButton.classList.add('d-none');
                } else {
                    noRetainButton.classList.remove('disabled');
                    tooltipWrapper.removeAttribute('data-tooltip');
                }
            }
        },
    });

    publicWidget.registry.SubscriptionCloseFinish = publicWidget.Widget.extend({
        selector: '.subscription-close-finish',
        events: {
            'click': '_onClick',
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _onClick: function () {
            this.$el.attr('disabled', true);
            this.$el.prepend('<i class="fa fa-refresh fa-spin"></i> ');
            $('#wc-modal-close-init form').submit();
        },
    });
