/** @odoo-module */
import { registry } from "@web/core/registry";
import { useInputField } from "@web/views/fields/input_field_hook";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
const { Component, useRef, onMounted, onWillStart, useState } = owl;
var rpc = require('web.rpc');
export class AddressAutocompleteFieldError extends Error {}
export class AddressAutocompleteField extends Component {
    static template = 'FieldAddressAutocomplete';

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.input = useRef('inputAddress');
        this.mapContainer = useRef('mapContainer');
        this.state = useState({ apiKeyAvailable: true });

        useInputField({ getValue: () => this.props.value || "", refName: "inputAddress" });

        onMounted(() => {
            // Ensure Google Maps API is loaded before initializing autocomplete
            if (typeof google !== 'undefined' && google.maps && google.maps.places) {
                this.initializeAutocomplete();
                this.initializeMap();
            } else {
                window.initMap = () => {
                    this.initializeAutocomplete();
                    this.initializeMap();
                };
            }
        });

        onWillStart(async () => {
            // Fetch API key from server
            let apiKey;
            try {
                apiKey = await rpc.query({
                    model: 'res.google.api',
                    method: 'api_key_get',
                    args: [],
                });               
            } catch (error) {  
                this.state.apiKeyAvailable = false;              
                return;
            }

            if (!apiKey) {    
                this.state.apiKeyAvailable = false;           
                return;
            }
            try {
                await loadJS(
                    `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=initMap`
                );                
            } catch (error) {
                this.state.apiKeyAvailable = false;
                return;              
            }
            
            // Load jQuery from CDN
            const jQueryScript = document.createElement('script');
            jQueryScript.src = 'https://code.jquery.com/jquery-3.6.0.min.js';
            jQueryScript.onload = () => {
                this.initializeJQuery();
            };
            document.head.appendChild(jQueryScript);
        });
    }

    initializeJQuery() {
        var $ = jQuery.noConflict(true);
        $(document).ready(function() {
            $('.o_content').on('scroll', function() {                
                $('.pac-container').hide();
            });
            $('.o_form_sheet_bg').on('scroll', function() {
                $('.pac-container').hide();
            }); 
        });
    }

    initializeAutocomplete() {
        if (this.input.el) {
            const autocomplete = new google.maps.places.Autocomplete(this.input.el, {
                types: ['address'],
            });

            // Add input validation
            this.input.el.addEventListener('input', () => {
                this.validateInput(this.input.el.value);
            });

            autocomplete.addListener('place_changed', async () => {
                const place = autocomplete.getPlace();
                if (place.geometry) {
                    this.props.update(place.formatted_address);
                    this.updateMap(place.geometry.location);
                    const addressComponents = place.address_components;

                    let state = "";
                    let country = "";
                    let city = "";
                    let zip = "";
                    let street = "";
                    let street_2 = "";
                    let country_abbr = "";
                    let crm_city = "";
                    let crm_state = "";
                    let crm_country = "";
                    let crm_zip = "";
                    let crm_street = "";
                    let crm_street_2 = "";
            
                    for (const component of addressComponents) {
                        if (component.types.includes("locality")) {
                            city = component.long_name;
                            crm_city = component.long_name;
                        }
                        if (component.types.includes("administrative_area_level_1")) {
                            state = component.long_name;
                            crm_state = component.long_name;
                        }
                        if (component.types.includes("country")) {
                            country = component.long_name; // Using short_name to get country code (IN)
                            country_abbr = component.short_name;
                            crm_country = component.long_name;
                        }
                        if (component.types.includes("postal_code")) {
                            zip = component.long_name;
                            crm_zip = component.long_name;
                        }
                        if (component.types.includes("route")) {
                            street = component.long_name;
                            crm_street = component.long_name;
                        }
                        if (component.types.includes("street_number")) {
                            street_2 = component.long_name;
                            crm_street_2 = component.long_name;
                        }  
                    }
            
                    // Combine state and country into the desired format
                    const stateCountry = `${state} (${country_abbr})`;                   
                    
                    // Update the existing country and state fields with the fetched IDs
                    const stateField = document.getElementById("state_id");
                    if (stateField) {
                        stateField.value = stateCountry;
                    }
                    const crmstateField = document.getElementById("state_id_1");
                    if (crmstateField) {
                        crmstateField.value = stateCountry;
                    }
                    const statelabelField = document.getElementById("state_label");
                    if (statelabelField) {
                        setTimeout(() => {                       
                        statelabelField.value = state;
                        }, 10);
                    }
                    //crm state
                    const crmstatelabelField = document.getElementById("state_label");
                    if (crmstatelabelField) {
                        setTimeout(() => {
                        crmstatelabelField.value = crm_state;
                        }, 10);
                    }
                    const countrylabelField = document.getElementById("country_label");
                    if (countrylabelField) {
                        setTimeout(() => {
                        countrylabelField.value = country;
                        }, 10);
                    }
                   
                    const countryField = document.getElementById("country_id");
                    if (countryField) {
                        countryField.value = country;
                    }
                    const crmcountryField = document.getElementById("country_id_1");
                    if (crmcountryField) {
                        crmcountryField.value = crm_country;
                    }
                    const cityField = document.getElementById("city");
                    if (cityField) {
                        setTimeout(() => {
                            cityField.value = city;                            
                        }, 10);
                    }
                    const crmcityField = document.getElementById("city_1");
                    if (crmcityField) {
                        setTimeout(() => {
                            crmcityField.value = crm_city;                            
                        }, 10);
                    }
            
                    const zipField = document.getElementById("zip");
                    if (zipField) {
                        setTimeout(() => {
                            zipField.value = zip;                          
                        }, 10);                        
                    }
                    const crmzipField = document.getElementById("zip_1");
                    if (crmzipField) {
                        setTimeout(() => {
                            crmzipField.value = crm_zip;                          
                        }, 10);                        
                    }
            
                    const streetField = document.getElementById("street");
                    if (streetField) {
                        setTimeout(() => {
                            streetField.value = street;                            
                        }, 10);
                    }
                    const crmstreetField = document.getElementById("street_1");
                    if (crmstreetField) {
                        setTimeout(() => {
                            crmstreetField.value = crm_street;                            
                        }, 10);
                    }
            
                    const street2Field = document.getElementById("street2");
                    if (street2Field) {
                        setTimeout(() => {
                            street2Field.value = street_2;                            
                        }, 10);                        
                    }

                    const crmstreet2Field = document.getElementById("street2_1");
                    if (crmstreet2Field) {
                        setTimeout(() => {
                            crmstreet2Field.value = crm_street_2;                            
                        }, 10);                        
                    }
                }
            });
        }
    }

    validateInput(value) {
        const regex = /[^a-zA-Z0-9.,-\s]/;
        if (regex.test(value)) {
            console.error(`Invalid address input: ${value}`); // Log the problematic value
            this.input.el.value = ''; // Clear the input field
            throw new AddressAutocompleteFieldError(`Please enter a valid address without special characters.`);
        }
    }
    
    

    initializeMap() {
        const defaultLocation = { lat: 37.7749, lng: -122.4194 }; 
        // Default location (San Francisco, CA)
        if (this.mapContainer.el) {
            const map = new google.maps.Map(this.mapContainer.el, {
                center: defaultLocation,
                zoom: 15,
            });

            new google.maps.Marker({
                position: defaultLocation,
                map: map,
            });
        }
    }

    updateMap(location) {
        if (this.mapContainer.el) {
            const map = new google.maps.Map(this.mapContainer.el, {
                center: location,
                zoom: 15,
            });

            new google.maps.Marker({
                position: location,
                map: map,
            });
        }
    }
}

registry.category("fields").add("address_autocomplete", AddressAutocompleteField);
