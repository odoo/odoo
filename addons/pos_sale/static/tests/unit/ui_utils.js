import { animationFrame, click, waitFor, waitUntil } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    clickControlButton,
    isMobile,
    sendBufferKeys,
} from "@point_of_sale/../tests/unit/ui_utils";
import { expect } from "@odoo/hoot";

const waitUntilDialogsClosed = () => waitUntil(() => !document.querySelector(".modal"));

// The quotations are listed in a list view on desktop and in a kanban view on mobile.
const quotationRow = () =>
    isMobile() ? ".modal .o_kanban_record:not(.o_kanban_ghost)" : ".modal .o_data_row";
const quotationCell = () =>
    isMobile() ? ".modal .o_kanban_record:not(.o_kanban_ghost)" : ".modal .o_data_row .o_data_cell";

export async function openQuotationList() {
    await clickControlButton("Quotation / Order");
    await waitFor(isMobile() ? ".modal .o_kanban_view" : ".modal .o_list_view");
}

export async function selectQuotation(saleOrderName) {
    await openQuotationList();
    await contains(`${quotationCell()}:contains("${saleOrderName}")`).click();
    await waitFor(`.modal .selection-item`);
}

export function isQuotationListed(saleOrderName) {
    return [...document.querySelectorAll(quotationRow())].some((row) =>
        row.textContent.includes(saleOrderName)
    );
}

export function listedQuotationsCount() {
    return document.querySelectorAll(quotationRow()).length;
}

export async function settleSaleOrder(saleOrderName, { loadSN } = {}) {
    await selectQuotation(saleOrderName);
    await contains(`.modal .selection-item:contains("Settle the order")`).click();
    if (loadSN !== undefined) {
        await waitFor(
            `.modal:contains("Do you want to load the SN/Lots linked to the Sales Order?")`
        );
        await contains(`.modal .btn:contains("${loadSN ? "Ok" : "Discard"}")`).click();
    }
    await waitUntilDialogsClosed();
    await animationFrame();
}

export async function downPaymentSaleOrder(saleOrderName, amount, { percentage } = {}) {
    const label = percentage
        ? "Apply a down payment (percentage)"
        : "Apply a down payment (fixed amount)";
    await selectQuotation(saleOrderName);
    await contains(`.modal .selection-item:contains("${label}")`).click();
    await waitFor(`.modal .modal-title:contains("Down Payment")`);
    await sendBufferKeys(amount);
    await click(`.modal .modal-footer .btn:contains("Apply")`);
    await waitUntilDialogsClosed();
    await animationFrame();
}

export const toggleSearchBar = async () => contains(".o_searchview_dropdown_toggler").click();
export const removeFilter = async (filterName) =>
    contains(
        `.o_searchview_input_container .o_facet_values:contains("${filterName}") .o_facet_remove`
    ).click();

export async function selectFilter(filterName) {
    await toggleSearchBar();
    await contains(`.o_filter_menu .o_menu_item:contains(${filterName})`).click();
    await toggleSearchBar();
}

export async function settlePaidSaleOrder(saleOrderName) {
    await openQuotationList();
    expect(isQuotationListed(saleOrderName)).toBe(false);
    await selectFilter("Paid");
    expect(isQuotationListed(saleOrderName)).toBe(true);
    await contains(`${quotationCell()}:contains("${saleOrderName}")`).click();
    await waitUntilDialogsClosed();
    await animationFrame();
}
