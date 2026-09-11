/** @odoo-module */
import { registry } from "@web/core/registry";
import { useInputField } from "@web/views/fields/input_field_hook";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

const { Component, useRef, onMounted, onWillStart, useState } = owl;
var rpc = require('web.rpc');

export class FieldCityGeoLocationAutocomplete extends Component {
    static template = 'FieldCityGeoLocationAutocomplete';

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.input = useRef('inputCity');
        this.state = useState({ apiKeyAvailable: true });

        const latFieldName = this.props.record.activeFields[this.props.id].options.latFieldName || 'latitude';
        const longFieldName = this.props.record.activeFields[this.props.id].options.longFieldName || 'longitude';
        const inputFiledName = this.props.id || '';

        this.latFieldName = latFieldName;
        this.longFieldName = longFieldName;
        this.inputFiledName = inputFiledName;

        useInputField({
            getValue: () => this.props.value || "",
            setValue: (newValue) => {
                // Directly update the record's data
                this.props.record.data[latFieldName] = newValue.latitude;
                this.props.record.data[longFieldName] = newValue.longitude;
                this.input.el.value = newValue.city || "";
            },
            refName: "inputCity",
        });

        onMounted(() => {
            if (typeof google !== 'undefined' && google.maps && google.maps.places) {
                this.initializeAutocomplete();
            } else {
                window.initMap = () => {
                    this.initializeAutocomplete();
                };
            }
        });

        onWillStart(async () => {
            try {
                    const companyId = this.props.record.data.company_id[0]; // Assuming you have access to the company ID
                    const apiKey = await rpc.query({
                        model: 'res.company',
                        method: 'read',
                        args: [companyId, ['google_api_key']], // Adjust the field name as necessary
                    });

                    if (!apiKey || !apiKey[0] || !apiKey[0].google_api_key) {
                        throw new Error("API Key not found.");
                    }

                    await loadJS(`https://maps.googleapis.com/maps/api/js?key=${apiKey[0].google_api_key}&libraries=places`);
                } catch (error) {
                    console.error("Error loading API key or Google Maps script:", error);
                    this.state.apiKeyAvailable = false;
                }
        });
    }

    initializeAutocomplete() {
        if (this.input.el) {
            const autocomplete = new google.maps.places.Autocomplete(this.input.el, {
                types: ['(cities)'],
                componentRestrictions: { country: 'IN' }
            });

            autocomplete.addListener('place_changed', () => {
                const place = autocomplete.getPlace();
                if (place.geometry) {
                    const latitude = place.geometry.location.lat();
                    const longitude = place.geometry.location.lng();

                    // Update latitude and longitude directly in the record's data
                    this.props.record.data[this.latFieldName] = latitude;
                    this.props.record.data[this.longFieldName] = longitude;

                    const city = place.formatted_address || "";
                    this.props.record.update({ [this.latFieldName]: latitude, [this.longFieldName]: longitude, [this.inputFiledName]: city });
                }
            });
        }
    }

    getCityFromAddressComponents(addressComponents) {
        let city = null;
        let state = null;

        for (const component of addressComponents) {
            // Check for city
            if (component.types.includes('locality')) {
                city = component.long_name;
            }
            // Check for state (administrative area level 1)
            if (component.types.includes('administrative_area_level_1')) {
                state = component.long_name;
            }
            // Optionally check for sublocality or fallback if city is not found
            if (!city && component.types.includes('sublocality')) {
                city = component.long_name;
            }
        }

        // Return formatted City, State or just City if state is not available
        if (city && state) {
            return `${city}, ${state}`;
        } else if (city) {
            return city;
        }
        return null;
    }
}

registry.category("fields").add("geo_locator_widget", FieldCityGeoLocationAutocomplete);
