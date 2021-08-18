/** @odoo-module **/

import publicWidget from "web.public.widget";
import "website_sale_delivery.checkout";
import {qweb as QWeb} from "web.core";

const WebsiteSaleDeliveryWidget = publicWidget.registry.websiteSaleDelivery;


WebsiteSaleDeliveryWidget.include({
    xmlDependencies: (WebsiteSaleDeliveryWidget.prototype.xmlDependencies || []).concat([
        '/website_sale_delivery_mondialrelay/static/src/xml/website_sale_delivery_mondialrelay.xml',
    ]),
    events: _.extend({
        "click #btn_confirm_relay": "_onClickBtnConfirmRelay",
    }, WebsiteSaleDeliveryWidget.prototype.events),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Loads Mondial Relay the first time, else show it.
     *
     * @override
     */
    _handleCarrierUpdateResult: function (result) {
        this._super(...arguments);
        if (result.mondial_relay) {
            if (!$('#modal_mondialrelay').length) {
                this._loadMondialRelayModal(result);
            } else {
                this.$modal_mondialrelay.find('#btn_confirm_relay').toggleClass('disabled', !result.mondial_relay.current);
                this.$modal_mondialrelay.modal('show');
            }
        }
    },
    /**
     * This method render the modal, and inject it in dom with the Modial Relay Widgets script.
     * Once script loaded, it initialize the widget pre-configured with the information of result
     *
     * @private
     *
     * @param {Object} result: dict returned by call of _update_website_sale_delivery_return (python)
     */
    _loadMondialRelayModal: function (result) {
        // add modal to body and bind 'save' button
        $(QWeb.render('website_sale_delivery_mondialrelay', {})).appendTo('body');
        this.$modal_mondialrelay = $('#modal_mondialrelay');
        this.$modal_mondialrelay.find('#btn_confirm_relay').on('click', this._onClickBtnConfirmRelay.bind(this));

        // load mondial relay script
        const script = document.createElement('script');
        script.src = "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js";
        script.onload = () => {
            // instanciate MondialRelay widget
            const params = {
                Target: "", // required but handled by OnParcelShopSelected
                Brand: result.mondial_relay.brand,
                ColLivMod: result.mondial_relay.col_liv_mod,
                AllowedCountries: result.mondial_relay.allowed_countries,
                Country: result.mondial_relay.partner_country_code,
                PostCode: result.mondial_relay.partner_zip,
                Responsive: true,
                ShowResultsOnMap: true,
                AutoSelect: result.mondial_relay.current,
                OnParcelShopSelected: (RelaySelected) => {
                    this.lastRelaySelected = RelaySelected;
                    this.$modal_mondialrelay.find('#btn_confirm_relay').removeClass('disabled');
                },
            };
            this.$modal_mondialrelay.find('#o_zone_widget').MR_ParcelShopPicker(params);
            this.$modal_mondialrelay.modal('show');
            this.$modal_mondialrelay.find('#o_zone_widget').trigger("MR_RebindMap");
        };
        document.body.appendChild(script);

    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------


    /**
     * Update the shipping address on the order and refresh the UI.
     *
     * @private
     *
     */
    _onClickBtnConfirmRelay: function () {
        if (!this.lastRelaySelected) {
            return;
        }
        this._rpc({
            route: '/website_sale_delivery_mondialrelay/update_shipping',
            params: {
                ...this.lastRelaySelected,
            },
        }).then((o) => {
            $('#address_on_payment').html(o.address);
            this.$modal_mondialrelay.modal('hide');
        });
    },
});
