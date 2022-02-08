/** @odoo-module **/

import AbstractField from 'web.AbstractField';
import fieldRegistry from 'web.field_registry';

// temporary for OnNoResultReturned bug
import {registry} from "@web/core/registry";
import {UncaughtCorsError} from "@web/core/errors/error_service";
const errorHandlerRegistry = registry.category("error_handlers");

function corsIgnoredErrorHandler(env, error) {
    if (error instanceof UncaughtCorsError) {
        return true;
    }
}

var MondialRelayWidget = AbstractField.extend({
    resetOnAnyFieldChange: true,
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        if (this.recordData.is_mondialrelay) {
            if (!this.mondialRelayInitialized) {
                const script = document.createElement('script');
                script.src = "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js";
                script.onload = () => {
                    this.mondialRelayInitialized = true;
                    this._loadWidget();
                };
                document.body.appendChild(script);
            } else {
                this._loadWidget();
            }
        } else {
            this.$el.hide();
        }
    },

   /**
     *
     * @private
     */
    _loadWidget: function () {
        const params = {
            Target: "", // required but handled by OnParcelShopSelected
            Brand: this.recordData.mondialrelay_brand,
            ColLivMod: this.recordData.mondial_realy_colLivMod,
            AllowedCountries: this.recordData.mondialrelay_allowed_countries,
            PostCode: this.recordData.shipping_zip || '',
            Country: this.recordData.shipping_country_code  || '',
            Responsive: true,
            ShowResultsOnMap: true,
            AutoSelect: this.recordData.mondialrelay_last_selected_id,
            OnParcelShopSelected: (RelaySelected) => {
                const values = JSON.stringify({
                    'id': RelaySelected.ID,
                    'name': RelaySelected.Nom,
                    'street': RelaySelected.Adresse1,
                    'street2': RelaySelected.Adresse2,
                    'zip': RelaySelected.CP,
                    'city': RelaySelected.Ville,
                    'country': RelaySelected.Pays,
                });
                this._setValue(values);
            },
            OnNoResultReturned: () => {
                // HACK while Mondial Relay fix his bug
                // disable corsErrorHandler for 10 seconds
                // If code postal not valid, it will crash with Cors Error:
                // Cannot read property 'on' of undefined at u.MR_FitBounds
                const randInt = Math.floor(Math.random() * 100);
                errorHandlerRegistry.add("corsIgnoredErrorHandler" + randInt, corsIgnoredErrorHandler, {sequence: 10});
                setTimeout(function () {
                    errorHandlerRegistry.remove("corsIgnoredErrorHandler" + randInt);
                }, 10000);
            },
        };
        this.$el.show();
        this.$el.MR_ParcelShopPicker(params);
        this.$el.trigger("MR_RebindMap");
    },

});

fieldRegistry.add("mondialrelay_relay", MondialRelayWidget);
