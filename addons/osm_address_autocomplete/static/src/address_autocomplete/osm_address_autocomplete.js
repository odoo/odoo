import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useChildRef } from "@web/core/utils/hooks";
import { useInputField } from "@web/views/fields/input_field_hook";
import { rpc } from "@web/core/network/rpc";

const standardAddressFields = {
    street: {
        label: _t("Street field"),
        type: ["char"],
    },
    street_number: {
        label: _t("Street Number field"),
        type: ["char"],
    },
    street2: {
        label: _t("Street 2 field"),
        type: ["char"],
    },
    city: {
        label: _t("City field"),
        type: ["char"],
    },
    state_id: {
        label: _t("State field"),
        type: ["char", "many2one"],
    },
    zip: {
        label: _t("Zip field"),
        type: ["char"],
    },
    country_id: {
        label: _t("Country field"),
        type: ["char", "many2one"],
    },
};

export class OSMAddressAutoComplete extends CharField {
    static template = "osm_address_autocomplete.AddressAutoCompleteTemplate";
    static components = { AutoComplete, ...CharField.components };

    static props = {
        ...CharField.props,
        addressFieldMap: {
            type: Object,
            optional: true,
        },
    };

    static defaultProps = {
        ...CharField.defaultProps,
        addressFieldMap: {},
    };

    setup() {
        super.setup();
        this.input = useChildRef();
        useInputField({
            ref: this.input,
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
        });
    }

    _parseStreetAndNumber(text) {
        if (!text || typeof text !== "string") {
            return { street: null, number: null };
        }

        const trimmed = text.trim();
        const endMatch = trimmed.match(/^(.*?)(?:,?\s+)(\d+\w*)$/);
        if (endMatch && endMatch[1]) {
            return { street: endMatch[1].trim(), number: endMatch[2] };
        }

        const startMatch = trimmed.match(/^(\d+\w*)\s+(.*)$/);
        if (startMatch && startMatch[2]) {
            return { street: startMatch[2].trim(), number: startMatch[1] };
        }

        return { street: null, number: null };
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (request.length <= 3) {
                        return [];
                    }
                    const countryField = this.props.addressFieldMap.country_id || "country_id";
                    const countryValue = this.props.record.data[countryField];
                    const countryId = countryValue && (countryValue.id || countryValue[0]);

                    // Obtener ciudad y provincia actuales del formulario si existen
                    const cityField = this.props.addressFieldMap.city || "city";
                    const stateField = this.props.addressFieldMap.state_id || "state_id";
                    
                    let cityName = this.props.record.data[cityField] || "";
                    let stateName = this.props.record.data[stateField] || "";
                    
                    // Si state_id es many2one, obtener el nombre mostrado
                    if (stateName && typeof stateName === 'object') {
                        stateName = stateName.display_name || stateName[1] || "";
                    }

                    const suggestions = await rpc("/osm/autocomplete/address", {
                        partial_address: request,
                        country_id: countryId || null,
                        city_name: cityName.trim() || null,
                        state_name: stateName.toString().trim() || null,
                    });

                    return (suggestions.results || []).map((result) => ({
                        label: result.formatted_address,
                        onSelect: () => this.selectAddressProposition(result, countryId || false),
                    }));
                },
                optionSlot: "option",
                placeholder: _t("Searching for addresses..."),
            },
        ];
    }

    async selectAddressProposition(option, countryId) {
        const baseLabel = option && option.label;
        if (baseLabel) {
            this.props.record.update({ [this.props.name]: baseLabel });
            if (this.input.el) {
                this.input.el.value = baseLabel;
            }
        }

        const address = await rpc("/osm/autocomplete/details", {
            place_id: option.place_id,
            country_id: countryId || null,
        });

        console.log("📍 Address Response from Backend:", address);

        if (!address || !Object.keys(address).length) {
            if (option && option.label) {
                this.props.record.update({ [this.props.name]: option.label });
            }
            return;
        }

        const fieldsToUpdate = ["street", "street_number", "street2", "city", "zip", "state_id", "country_id", "latitude", "longitude"];
        const fields = this.props.record.fields;
        const addressFieldMap = this.props.addressFieldMap;

        const valuesToUpdate = {};

        const streetFieldName = addressFieldMap.street || "street";
        const fallbackLabel = option && option.label;
        const parsedStreet = this._parseStreetAndNumber(address.street || fallbackLabel || "");
        const selectedStreet = address.street || parsedStreet.street || fallbackLabel;
        if (selectedStreet) {
            valuesToUpdate[streetFieldName] = selectedStreet;
            if (this.props.name === streetFieldName) {
                valuesToUpdate[this.props.name] = selectedStreet;
            }
        }
        
        fieldsToUpdate.forEach((fieldName) => {
            let value = null;
            const recordFieldName = addressFieldMap[fieldName] || fieldName;
            
            // Solo procesar si el campo existe en el modelo
            if (!(recordFieldName in fields)) {
                console.warn(`⚠️ Field ${recordFieldName} not in model`);
                return;
            }
            
            // Mapeo de campos a fuentes en la respuesta
            if (fieldName === "street") {
                value = address.street || parsedStreet.street || (option && option.label);
            } else if (fieldName === "street_number") {
                value = address.street_number || parsedStreet.number;
            } else if (fieldName === "street2") {
                value = address.street2;
            } else if (fieldName === "city") {
                value = address.city;
            } else if (fieldName === "zip") {
                value = address.zip;
            } else if (fieldName === "state_id") {
                // Intentar obtener state como [id, name], sino state_name como texto
                value = address.state || address.state_name;
            } else if (fieldName === "country_id") {
                value = address.country;
            } else if (fieldName === "latitude") {
                // Asegurar que es un número (incluir 0 como valor válido)
                if (address.latitude !== undefined && address.latitude !== null && address.latitude !== "") {
                    const parsed = parseFloat(address.latitude);
                    if (!isNaN(parsed)) {
                        value = parsed;
                    }
                }
            } else if (fieldName === "longitude") {
                // Asegurar que es un número (incluir 0 como valor válido)
                if (address.longitude !== undefined && address.longitude !== null && address.longitude !== "") {
                    const parsed = parseFloat(address.longitude);
                    if (!isNaN(parsed)) {
                        value = parsed;
                    }
                }
            }
            
            if (value === null || value === undefined || value === "") {
                console.log(`⚠️ No value for ${fieldName}`);
                return;
            }
            
            // Convertir arrays [id, name] a objetos para many2one
            if (fields[recordFieldName] && fields[recordFieldName].type === "many2one") {
                if (Array.isArray(value)) {
                    value = { id: value[0], display_name: value[1] };
                } else if (typeof value === "string") {
                    console.log(`⚠️ Skipping ${recordFieldName} because value is not a valid many2one`);
                    return;
                }
            }
            
            console.log(`✅ Setting ${recordFieldName} = `, value);
            valuesToUpdate[recordFieldName] = value;
        });
        
        console.log("📦 Values to Update:", valuesToUpdate);
        
        if (Object.keys(valuesToUpdate).length > 0) {
            this.props.record.update(valuesToUpdate);
            if (selectedStreet && this.props.name === streetFieldName && this.input.el) {
                this.input.el.value = selectedStreet;
            }
            console.log("✅ Record updated!");
        } else {
            console.warn("❌ No values to update");
        }
    }
}

export const osmAddressAutoComplete = {
    ...charField,
    component: OSMAddressAutoComplete,
    displayName: _t("OSM Address AutoComplete"),
    supportedTypes: ["char"],
    supportedOptions: [
        ...charField.supportedOptions,
        ...Object.entries(standardAddressFields).map(([fname, data]) => ({
            label: data.label,
            placeholder: fname,
            type: "field",
            name: fname,
            availableTypes: data.type,
        })),
    ],
    extractProps: (fieldInfo, dynamicInfo) => {
        const { options } = fieldInfo;
        const props = charField.extractProps(fieldInfo, dynamicInfo);
        const addressFieldMap = {};
        Object.keys(standardAddressFields).forEach((fname) => {
            const optionValue = options[fname];
            if (optionValue) {
                addressFieldMap[fname] = optionValue;
            }
        });
        props.addressFieldMap = addressFieldMap;
        return props;
    },
};

registry.category("fields").add("osm_address_autocomplete", osmAddressAutoComplete);
