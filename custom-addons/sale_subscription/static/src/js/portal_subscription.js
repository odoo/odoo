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
            $('.subscription-close-message').add('.subscription-close-link')
                .hide()
                .filter((i, e) => $(e).attr('data-id') == reasonId)
                .show();

            $('.subscription-close-init-retain').addClass('d-none');
            $('.subscription-close-init-noretain').addClass('d-none');
            if (reasonId) {
                if (this.$el.children(':selected').attr('data-retention')) {
                    $('.subscription-close-init-retain').removeClass('d-none');
                } else {
                    $('.subscription-close-init-noretain').removeClass('d-none');
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
