import { registry } from "@web/core/registry";
import { loadBundle, loadJS } from "@web/core/assets";

// temporary for OnNoResultReturned bug
import { ThirdPartyScriptError } from "@web/core/errors/error_service";
const errorHandlerRegistry = registry.category("error_handlers");
import { Component, xml, signal, onWillStart, onMounted } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MONDIALRELAY_SCRIPT_URL = "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js"

function corsIgnoredErrorHandler(env, error) {
    if (error instanceof ThirdPartyScriptError) {
        return true;
    }
}

export class MondialRelayField extends Component {
    static template = xml`<div t-ref="this.root"/>`;
    static props = {...standardFieldProps};
    setup() {
        this.root = signal(null);
        onWillStart(async () => {
            await loadBundle("web._assets_jquery");
            await loadJS(MONDIALRELAY_SCRIPT_URL);
        });
        onMounted(() => {
            this.insertWidget($(this.root()));
        });
    }

    insertWidget($el) {
        const params = {
            Target: "", // required but handled by OnParcelShopSelected
            Brand: this.props.record.data.mondialrelay_brand,
            ColLivMod: this.props.record.data.mondialrelay_colLivMod,
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
                this.props.record.update({ [this.props.name]: values });
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

export const mondialRelayField = {
    component: MondialRelayField,
};

registry.category("fields").add("mondialrelay_relay", mondialRelayField);
