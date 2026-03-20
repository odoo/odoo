import { accountTourSteps } from "@account/js/tours/account";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('invoice_payments_widget_exchange_tour', {
    url: "/odoo",
    steps: () => [
    ...accountTourSteps.goToAccountMenu("Go to Invoicing"),
    {
        content: "Go to Customers",
        trigger: 'span:contains("Customers")',
        run: "click",
    },
    {
        content: "Go to Invoices",
        trigger: 'a:contains("Invoices")',
        run: "click",
    },
    {
        trigger: ".o_breadcrumb .text-truncate:contains(Invoices)",
    },
    {
        content: "Open first invoice",
        trigger: 'div.o_list_renderer table.o_list_table tbody tr.o_data_row:last > td.o_data_cell[name="name"]',
        run: "click",
    },
    {
        content: "Check payment widget is shown",
        trigger: 'div.o_field_widget.o_field_payment[name="invoice_payments_widget"]',
    },
    {
        content: "Check payment widget total exchange amount",
        trigger: 'div.o_field_widget.o_field_payment[name="invoice_payments_widget"] tr:last > td:last > i.o_field_widget span.exchange_amount:contains($ 150.00)',
    },
    {
        content: "Check payment widget total exchange is loss",
        trigger: 'div.o_field_widget.o_field_payment[name="invoice_payments_widget"] tr:last > td:last > i.o_field_widget span.exchange_label:contains(Exchange Loss)',
    },
    {
        content: "Go to next invoice",
        trigger: 'nav.o_pager button.o_pager_next',
        run: "click",
    },
    {
        content: "Check payment widget is shown",
        trigger: 'div.o_field_widget.o_field_payment[name="invoice_payments_widget"]',
    },
    {
        content: "Check payment widget total exchange amount",
        trigger: 'div.o_field_widget.o_field_payment[name="invoice_payments_widget"] tr:last > td:last > i.o_field_widget span.exchange_amount:contains($ 50.00)',
    },
    {
        content: "Check payment widget total exchange is loss",
        trigger: 'div.o_field_widget.o_field_payment[name="invoice_payments_widget"] tr:last > td:last > i.o_field_widget span.exchange_label:contains(Exchange Profit)',
    },
    {
        content: "Go to exchange line list view",
        trigger: 'a.js_exchange_info',
        run: "click",
    },
    {
        content: "Reconciled journal items are shown",
        trigger: '.o_breadcrumb .text-truncate:contains(Journal Items)',
    },
    {
        content: "Open exchange move",
        trigger: 'div.o_list_renderer table.o_list_table tbody tr.o_data_row:last > td.o_data_cell[name="move_name"] div[name="move_name"] a:contains(EXCH)',
    },
]});
