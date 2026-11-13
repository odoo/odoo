import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { PortalHomeCounters } from "@portal/interactions/portal_home_counters";

setupInteractionWhiteList("portal.portal_home_counters");

describe.current.tags("interaction_dev");

beforeEach(() => {
    patchWithCleanup(PortalHomeCounters.prototype, {
        getCountersAlwaysDisplayed() {
            return ["invoice_count"];
        },
    });
});

function mockCounters(counts) {
    onRpc("/my/counters", async (request) => {
        const { params } = await request.json();
        return Object.fromEntries(Object.keys(params.counters).map((name) => [name, counts[name]]));
    });
}

function card(id, category, counter) {
    const counterEl = counter
        ? `<span class="o_portal_count d-none" data-placeholder_count="${counter}" data-category="${category}"></span>`
        : "";
    return `
        <div class="o_portal_index_card ${counter ? "d-none" : ""}" data-id="${id}" data-category="${category}" data-show-in-portal="true">
            <a href="#">${counterEl}</a>
        </div>`;
}

function home(...cards) {
    return `
        <div class="o_portal_my_home">
            <div class="o_portal_cards">${cards.join("")}</div>
            <div class="o_portal_doc_spinner"/>
        </div>`;
}

test("customer keeps an always displayed card at zero", async () => {
    mockCounters({ invoice_count: 0, ticket_count: 1 });
    await startInteractions(
        home(
            card("invoices", "client_category", "invoice_count"),
            card("tickets", "client_category", "ticket_count")
        )
    );
    expect("[data-id='invoices']").not.toHaveClass("d-none");
    expect("[data-id='tickets']").not.toHaveClass("d-none");
});

test("vendor does not get an always displayed card at zero", async () => {
    mockCounters({ invoice_count: 0, purchase_count: 2 });
    await startInteractions(
        home(
            card("invoices", "client_category", "invoice_count"),
            card("purchases", "vendor_category", "purchase_count")
        )
    );
    expect("[data-id='invoices']").toHaveClass("d-none");
    expect("[data-id='purchases']").not.toHaveClass("d-none");
});

test("vendor card shown from the session cache also counts", async () => {
    mockCounters({ invoice_count: 0 });
    await startInteractions(
        home(
            card("invoices", "client_category", "invoice_count"),
            card("purchases", "vendor_category")
        )
    );
    expect("[data-id='invoices']").toHaveClass("d-none");
});

test("card total only decides whether the card shows", async () => {
    mockCounters({ invoice_count: 0, ticket_count: 4 });
    await startInteractions(
        home(
            card("invoices", "client_category", "invoice_count"),
            card("tickets", "client_category", "ticket_count")
        )
    );
    expect("[data-id='tickets']").not.toHaveClass("d-none");
    expect("[data-placeholder_count='ticket_count']").toHaveClass("d-none");
    expect("[data-id='invoices']").not.toHaveClass("d-none");
    expect("[data-placeholder_count='invoice_count']").toHaveClass("d-none");
});

test("always displayed card with documents stays visible for a vendor", async () => {
    mockCounters({ invoice_count: 3, purchase_count: 2 });
    await startInteractions(
        home(
            card("invoices", "client_category", "invoice_count"),
            card("purchases", "vendor_category", "purchase_count")
        )
    );
    expect("[data-id='invoices']").not.toHaveClass("d-none");
});

function cardWithAlert(id, counter, alertCounter) {
    return `
        <div class="o_portal_index_card d-none" data-id="${id}" data-category="client_category" data-show-in-portal="true">
            <a href="#">
                <span class="o_portal_count d-none" data-placeholder_count="${counter}" data-category="client_category"></span>
                <span class="o_portal_badge badge bg-danger d-none" data-placeholder_count="${alertCounter}" data-category="alert"></span>
            </a>
        </div>`;
}

test("card with documents awaiting the user only shows the danger badge", async () => {
    mockCounters({ sign_count: 2, to_sign_count: 1 });
    await startInteractions(home(cardWithAlert("sign", "sign_count", "to_sign_count")));
    expect("[data-id='sign']").not.toHaveClass("d-none");
    expect("[data-placeholder_count='to_sign_count']").toHaveText("1");
    expect("[data-placeholder_count='to_sign_count']").not.toHaveClass("d-none");
    expect("[data-placeholder_count='sign_count']").toHaveClass("d-none");
});

test("card with no document awaiting the user shows no badge", async () => {
    mockCounters({ sign_count: 2, to_sign_count: 0 });
    await startInteractions(home(cardWithAlert("sign", "sign_count", "to_sign_count")));
    expect("[data-id='sign']").not.toHaveClass("d-none");
    expect("[data-placeholder_count='sign_count']").toHaveClass("d-none");
    expect("[data-placeholder_count='to_sign_count']").toHaveClass("d-none");
});
