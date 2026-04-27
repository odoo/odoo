/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_carrier_type_selection_field', { steps: () => [
    {
        content: 'Show the carrier type popup',
        trigger: 'button[name="action_get_carrier_type"]',
        run: 'click'
    },
    {
        content: 'Check if the dropdown was populated',
        trigger: '#carrier_type_0',
        run: function () {
            const carrierTypeSelect = document.querySelector('select#carrier_type_0');
            [
                '"FedEx"',
                '"DHL Global Mail"',
                '"USPS"',
                '"GSO"',
                '"DHL Express"',
                '"Canada Post"',
                '"Canpar"',
                '"DPD"',
                '"LSO"',
                '"UPSDAP"',
            ].forEach((carrierType) => {
                console.info(`Checking carrier type ${carrierType} ...`);
                carrierTypeSelect.value = carrierType;
                if (carrierTypeSelect.value != carrierType) {
                    console.error(`${carrierType} value not found in available carrier types.`);
                }
            })
            // Check an incorrect value and confirm that it was not selected
            var carrierType = 'CompletelyFakeCarrierType';
            carrierTypeSelect.value = carrierType;
            if (carrierTypeSelect.value == carrierType) {
                console.error(`${carrierType} value should not be allowed.`);
            }
        }
    },
    {
        content: "Discard the carrier type's modal",
        trigger: ".modal-footer button:contains('Cancel')",
        run: 'click',
    },
]});
