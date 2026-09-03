import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("invoicePoSOrderWithSelfInvocing", {
    steps: () => [
        {
            trigger: "input[name='pos_reference']",
            run: "edit 2500-002-00002",
        },
        {
            trigger: ".o_portal_wrap input[name='date_order']",
            run: function () {
                const date_order = luxon.DateTime.now();
                document.querySelector(".o_portal_wrap input[name='date_order']").value =
                    date_order.toFormat("yyyy-MM-dd");
            },
        },
        {
            trigger: ".o_portal_wrap input[name='ticket_code']",
            run: "edit inPoS",
        },
        {
            trigger: ".o_portal_wrap button:contains('Request Invoice')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_portal_wrap input[name='name']",
            run: "edit Anant Parmar",
        },
        {
            trigger: ".o_portal_wrap input[name='phone']",
            run: "edit +911234567890",
        },
        {
            trigger: ".o_portal_wrap input[name='email']",
            run: "edit test@test.com",
        },
        {
            trigger: ".o_portal_wrap input[name='company_name']",
            run: function () {
                const companyNameInput = document.querySelector("input[name='company_name']");
                if (companyNameInput.hasAttribute("readonly")) {
                    throw new Error("The company name input must not be readonly.");
                }
                companyNameInput.value = "TEST COMPANY NAME";
            },
        },
        {
            trigger: ".o_portal_wrap input[name='vat']",
            run: function () {
                const vatInput = document.querySelector("input[name='vat']");
                if (vatInput.hasAttribute("readonly")) {
                    throw new Error("The vat input must not be readonly.");
                }
                vatInput.value = "1234567890";
            },
        },
        {
            trigger: ".o_portal_wrap input[name='street']",
            run: "edit 131, Satyamcity society",
        },
        {
            trigger: ".o_portal_wrap input[name='street2']",
            run: "edit opposite new rto office",
        },
        {
            trigger: ".o_portal_wrap input[name='city']",
            run: "edit palanpur",
        },
        {
            trigger: ".o_portal_wrap input[name='zip']",
            run: "edit 385001",
        },
        {
            trigger: ".o_portal_wrap select[name='country_id']",
            run: function () {
                const countrySelect = document.querySelector("select[name='country_id']");
                if (Array.from(countrySelect.classList).includes("d-none")) {
                    throw new Error("The language selector must not be hidden.");
                }
                countrySelect.value = "233";
            },
        },
        {
            trigger: ".o_portal_wrap select[name='state_id']",
            run: function () {
                const stateSelect = document.querySelector("select[name='state_id']");
                if (Array.from(stateSelect.classList).includes("d-none")) {
                    throw new Error("The language selector must not be hidden.");
                }
                stateSelect.value = "19";
            },
        },
        {
            trigger: ".o_portal_wrap button:contains('Get my invoice')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".rounded.text-bg-success.fw-normal.badge",
        },
    ],
});
registry.category("web_tour.tours").add("invoicePoSOrderWithPartner", {
    steps: () => [
        {
            trigger: "input[name='pos_reference']",
            run: "edit 2500-002-00003",
        },
        {
            trigger: ".o_portal_wrap input[name='date_order']",
            run: function () {
                const date_order = luxon.DateTime.now();
                document.querySelector(".o_portal_wrap input[name='date_order']").value =
                    date_order.toFormat("yyyy-MM-dd");
            },
        },
        {
            trigger: ".o_portal_wrap input[name='ticket_code']",
            run: "edit inPoS",
        },
        {
            trigger: ".o_portal_wrap button:contains('Request Invoice')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_portal_wrap input[name='name']",
            run: function ({ anchor: nameInput }) {
                if (nameInput.value.trim() !== "Rangilo Gujarati") {
                    throw new Error("The name input must be prefilled with correct partner name.");
                }
            },
        },
        {
            trigger: ".o_portal_wrap input[name='vat']",
            run: function ({ anchor: vatInput }) {
                if (vatInput.value.trim() !== "24AAGCC7144L6ZE") {
                    throw new Error("The vat input must be prefilled with correct partner vat.");
                }
            },
        },
        {
            trigger: ".o_portal_wrap input[name='zip']",
            run: function ({ anchor: zipInput }) {
                if (zipInput.value.trim() !== "654321") {
                    throw new Error("The vat input must be prefilled with correct partner zip.");
                }
            },
        },
        {
            trigger: ".o_portal_wrap select[name='country_id']",
            run: function ({ anchor: countryInput }) {
                if (countryInput.value !== "104") {
                    throw new Error("The country must be selected to India.");
                }
            },
        },
        {
            trigger: ".o_portal_wrap select[name='state_id']",
            run: function ({ anchor: stateInput }) {
                if (stateInput.value !== "588") {
                    throw new Error("The state must be selected to Gujarat.");
                }
            },
        },
        {
            trigger: ".o_portal_wrap button:contains('Get my invoice')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".rounded.text-bg-success.fw-normal.badge",
        },
    ],
});
