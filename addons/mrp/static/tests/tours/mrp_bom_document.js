/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('test_mrp_bom_document_no_variant', {
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        ...stepUtils.goToAppSteps('mrp.menu_mrp_root'),
        {
            trigger: 'div.o_menu_sections > button > span:contains("Products")',
            run: "click",
        },
        {
            trigger: 'a.o-dropdown-item:contains("Bills of Materials")',
            run: "click",
        },
        {
            trigger: 'td.o_data_cell:contains("bom_product")',
            run: "click",
        },
        {
            trigger: 'tbody > tr:nth-child(1) > td[name="attachments_count"]:contains("2")',
        },
        {
            trigger: 'tbody > tr:nth-child(1) > td > button[name="action_see_attachments"]',
            run: "click",
        },
        {
            trigger: 'small:contains("Documents of this variant")',
        },
        {
            trigger: 'li.breadcrumb-item > a.fw-bold:contains("bom_product")',
            run: "click",
        },
        {
            trigger: 'span:contains("BoM Overview")',
            run: "click",
        },
        {
            trigger: 'tbody > tr:nth-child(2) > td > span > a.fa-files-o',
            run: "click",
        },
        {
            trigger: 'article',
            run: function () {
                const lines = document.querySelectorAll('article').length;
                if (lines !== 2) {
                    console.error("Should have found 2 documents");
                }
            },
        },
        {
            trigger: 'li.breadcrumb-item > a.fw-bold:contains("bom_product")',
            run: "click",
        },
        {
            trigger: 'tbody > tr:nth-child(2) > td[name="attachments_count"]:contains("2")',
        },
    ],
});

registry.category("web_tour.tours").add('test_mrp_bom_document', {
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        ...stepUtils.goToAppSteps('mrp.menu_mrp_root'),
        {
            trigger: 'div.o_menu_sections > button > span:contains("Products")',
            run: "click",
        },
        {
            trigger: 'a.o-dropdown-item:contains("Bills of Materials")',
            run: "click",
        },
        {
            trigger: 'td.o_data_cell:contains("bom_product")',
            run: "click",
        },
        {
            trigger: 'tbody > tr:nth-child(1) > td[name="attachments_count"]:contains("2")',
        },
        {
            trigger: 'tbody > tr:nth-child(1) > td > button[name="action_see_attachments"]',
            run: "click",
        },
        {
            trigger: 'small:contains("Documents of this variant")',
        },
        {
            trigger: 'li.breadcrumb-item > a.fw-bold:contains("bom_product")',
            run: "click",
        },
        {
            trigger: 'span:contains("BoM Overview")',
            run: "click",
        },
        {
            trigger: 'tbody > tr:nth-child(2) > td > span > a.fa-files-o',
            run: "click",
        },
        {
            trigger: 'article',
            run: function () {
                const lines = document.querySelectorAll('article').length;
                if (lines !== 2) {
                    console.error("Should have found 2 documents");
                }
            },
        },
        {
            trigger: 'li.breadcrumb-item > a.fw-bold:contains("bom_product")',
            run: "click",
        },
        {
            trigger: 'tbody > tr:nth-child(2) > td[name="attachments_count"]:contains("3")',
        },
    ],
});
