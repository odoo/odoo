/** @odoo-module */
import { registry } from '@web/core/registry';
import { useRef } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const { Component, onWillStart, useState, reactive } = owl;
import { PharmacyOrderLines } from "./pharmacy_orderlines";

var currency = 0;
var quantity = 0;
var amount = 0;
var sub_t = 0;
var sub_total = 0;
var product_lst = [];
var uom_lst = [];
var invoice = 0;
var invoice_id = 0;
var tax = 0;

export class PharmacyDashboard extends Component {
    setup() {
        super.setup();
        this.vaccine_div = useRef('vaccine_div')
        this.medicine_div = useRef('medicine_div')
        this.home_content = useRef('home_content')
        this.patient_search = useRef('PatientSearch');
        this.orders_div = useRef('orders_div')
        this.orm = useService('orm')
        this.user = user;
        this.actionService = useService("action");
        this.state = useState({
            product_lst: [],
            medicines: [],
            units: [],
            sub_total,
            vaccine: [],
            order_data: [],
            order_line: [],
            menu: 'home',
        });
        this.fetch_product();
        onWillStart(async () => {
            this.state.med = await this.orm.call('product.template', 'action_get_medicine_data', []);
        })
    }

    // Fetch product details
    async fetch_product() {
        const domain = [['medicine_ok', '=', true]];
        const result = await this.orm.call('product.template', 'search_read', [domain]);
        this.state.product_lst = result;
        this.create_order();
    }

    // Method for creating sale order
    async create_order() {
        this.state.menu = 'home';
        await this.orm.call('hospital.pharmacy', 'company_currency', [])
            .then((result) => {
                const currencyElements = document.querySelectorAll('[id^="symbol"]');
                currencyElements.forEach(el => {
                    el.textContent = result || '';
                });
            });
        this.state.medicines = await this.product_lst;
        this.state.units = await this.uom_lst;
    }

    // To update the orderline of sale order
    updateOrderLine(line, id) {
        const orderline = this.state.order_line.filter(orderline => orderline.id === id)[0]
        orderline.product = line.product
        orderline.qty = parseInt(line.qty)
        orderline.uom = line.uom
        orderline.price = line.price
        orderline.sub_total = line.sub_total
    }

    // To add new row in the sale order line
    addRow() {
    const newLine = reactive({
        id: Date.now(),
        product: false,
        qty: 1,
        uom: false,
        price: 0,
        sub_total: 0
    });
    const data = [...this.state.order_line, newLine];
    this.state.order_line = data;
}

    // To remove the line if not needed
    removeLine(id) {
        const filteredData = this.state.order_line.filter(line => line.id != id)
        this.state.order_line = filteredData
    }

    // Create sale order
    async create_sale_order() {
        var data = {};
        data['name'] = document.getElementById('patient-name').value;
        data['phone'] = document.getElementById('patient-phone').value;
        data['email'] = document.getElementById('patient-mail').value;
        data['dob'] = document.getElementById('o_patient-dob').value;
        data['products'] = this.state.order_line;
        const genderRadios = document.getElementsByName('gender');
        data['gender'] = 'male';
        for (let radio of genderRadios) {
            if (radio.checked) {
                data['gender'] = radio.value;
                break;
            }
        }
        const nameElement = document.getElementById('patient-name');
        const emailElement = document.getElementById('patient-mail');
        if (!nameElement || nameElement.value.trim() === "") {
            alert("Please enter the Name");
            return;
        }

        if (!emailElement || emailElement.value.trim() === "") {
            alert("Please enter the Email");
            return;
        }
        let hasInvalidQuantity = false;
        for (let line of this.state.order_line) {
            if (line.qty < 1) {
                hasInvalidQuantity = true;
                break;
            }
        }

        if (hasInvalidQuantity) {
            alert('Medicine quantity must be greater than or equal to 1.');
            return;
        }
        try {
            const result = await this.orm.call('hospital.pharmacy', 'create_sale_order', [data]);
            alert('The sale order has been created with reference number ' + result.invoice);
            window.location.reload();
        } catch (error) {
            console.error('Error creating sale order:', error);
            alert('Error creating sale order: ' + error.message);
        }
    }

    // Fetch patient data
    async fetch_patient_data() {
        const patientCode = this.patient_search.el.value;
        if (!patientCode) {
            alert("Please enter a patient code");
            return;
        }
        try {
            const result = await this.orm.call(
                'res.partner',
                'action_get_patient_data',
                [[this.patient_search.el.value]]
            );
            const patientTitle = document.getElementById('patient-title');
            if (patientTitle) {
                patientTitle.innerText = result.name || 'Not Found';
            }
            const patientCode = document.getElementById('patient-code');
            if (patientCode) {
                patientCode.innerText = result.unique || '';
            }
            const patientAge = document.getElementById('patient-age');
            if (patientAge) {
                patientAge.innerText = result.dob || '';
            }
            const patientBlood = document.getElementById('patient-blood');
            if (patientBlood) {
                patientBlood.innerText = result.blood_group || '';
            }
            const patientGender = result.gender || '';
            if (patientGender) {
                const genderRadios = document.getElementsByName('gender');
                genderRadios.forEach(radio => {
                    radio.checked = (radio.value === patientGender.toLowerCase());
                });
            }
            const patientImage = document.getElementById('patient-image');
            if (patientImage) {
                if (result.image_1920) {
                    patientImage.src = 'data:image/png;base64,' + result.image_1920;
                } else if (result.name === 'Patient Not Found') {
                    patientImage.src = 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png';
                }
            }
            if (result.name === 'Patient Not Found') {
                const histHead = document.getElementById('hist_head');
                if (histHead) histHead.innerHTML = '';
            }
        } catch (error) {
            console.error('Error fetching patient data:', error);
            alert('Error fetching patient data: ' + error.message);
        }
    }

    // Fetch medicine data while clicking Medicine button
    async fetch_medicine_data() {
        this.state.menu = 'medicines';
    }

    // Fetch vaccine data
    async fetch_vaccine_data() {
        this.state.menu = 'vaccines';
        this.state.vaccine = await this.orm.call('product.template', 'action_get_vaccine_data', []);
    }

    // Method for fetching all sale orders
    async fetch_sale_orders() {
        this.state.menu = 'orders';
        this.state.order_data = await this.orm.call('sale.order', 'search_read',
            [[['partner_id.patient_seq', 'not in', ['New', 'Employee', 'User']]], ['name', 'create_date', 'partner_id', 'amount_total', 'state']]);
    }

    // Method for emptying the data
    async clear_data() {
        this.patient_search.el.value = '';
        const histHead = document.getElementById('hist_head');
        if (histHead) histHead.innerHTML = '';
        document.getElementById('patient-title').textContent = '';
        document.getElementById('patient-code').textContent = '';
        document.getElementById('patient-gender').textContent = '';
        document.getElementById('patient-blood').textContent = '';
        const patientImage = document.getElementById('patient-image');
        patientImage.src = 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png';
    }
}

PharmacyDashboard.template = "PharmacyDashboard"
PharmacyDashboard.components = { PharmacyOrderLines }

registry.category("actions").add('pharmacy_dashboard_tags', PharmacyDashboard);
