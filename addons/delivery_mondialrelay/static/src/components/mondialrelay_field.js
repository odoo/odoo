/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";

// temporary for OnNoResultReturned bug
import { UncaughtCorsError } from "@web/core/errors/error_service";
const errorHandlerRegistry = registry.category("error_handlers");

const { Component, onWillRender, useEffect, useRef, useState, xml } = owl;

const MONDIALRELAY_SCRIPT_URL = "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js"

function corsIgnoredErrorHandler(env, error) {
    if (error instanceof UncaughtCorsError) {
        return true;
    }
}

export class MondialRelayField extends Component {
    setup() {
        this.root = useRef("root");
        this.state = useState({
            libLoaded: false, // Whether the library is loaded or not
        });
        onWillRender(() => {
            // Do nothing if the record is not of type mondial_relay
            if (!this.enabled || this.state.libLoaded) {
                return;
            }
            loadJS(MONDIALRELAY_SCRIPT_URL).then(() => {this.state.libLoaded = true});
        });

        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                this.insertWidget($(el));
            },
            () => [this.state.libLoaded && this.root.el],
        )
    }

    get enabled() {
        return this.props.record.data.is_mondialrelay;
    }

    insertWidget($el) {
        const params = {
            Target: "", // required but handled by OnParcelShopSelected
            Brand: this.props.record.data.mondialrelay_brand,
            ColLivMod: this.props.record.data.mondial_realy_colLivMod,
            AllowedCountries: this.props.record.data.mondialrelay_allowed_countries,
            PostCode: this.props.record.data.shipping_zip || '',
            Country: this.props.record.data.shipping_country_code  || '',
            Responsive: true,
            ShowResultsOnMap: true,
            AutoSelect: this.props.record.data.mondialrelay_last_selected_id,
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
                this.props.update(values);
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
        $el.show();
        $el.MR_ParcelShopPicker(params);
        $el.trigger("MR_RebindMap");
    }
}
MondialRelayField.template = xml`<div t-if="enabled" t-ref="root"/>`;

registry.category("fields").add("mondialrelay_relay", MondialRelayField);
