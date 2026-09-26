export function checkStoreOrdersShown() {
    return {
        content: "Check that the In Store Orders card is shown on the portal home",
        trigger: `.o_portal_index_card:not(.d-none) a[title='In Store Orders']`,
    };
}

export function openStoreOrders() {
    return {
        content: "Open the in store orders from the portal home",
        trigger: `.o_portal_index_card a[title='In Store Orders']`,
        run: "click",
        expectUnloadPage: true,
    };
}

export function checkOrderShown(reference) {
    return {
        content: `Check that order ${reference} is listed`,
        trigger: `.o_portal_my_doc_table tr:contains('${reference}')`,
    };
}

export function checkFirstOrder(reference) {
    return {
        content: `Check that order ${reference} is listed first`,
        trigger: `.o_portal_my_doc_table tbody tr:first-child td:contains('${reference}')`,
    };
}

export function checkReceiptLink(reference) {
    return {
        content: `Check that order ${reference} offers its receipt for download`,
        trigger:
            `.o_portal_my_doc_table tr:contains('${reference}')` +
            ` a.text-decoration-none[href^='/pos/receipt/'][href*='download=1']`,
    };
}

export function checkInvoiceLink(reference) {
    return {
        content: `Check that order ${reference} links to its invoice request`,
        trigger:
            `.o_portal_my_doc_table tr:contains('${reference}')` +
            ` a.text-decoration-none[target='_blank'][href*='/pos/ticket?order_uuid=']`,
    };
}

export function sortBy(sorting) {
    return [
        {
            content: "Open the sort menu",
            trigger: "#portal_searchbar_sortby",
            run: "click",
        },
        {
            content: `Sort on ${sorting}`,
            trigger: `div[aria-labelledby='portal_searchbar_sortby'] .dropdown-item[href*='sortby=${sorting}']`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
}

export function filterBy(filter) {
    return [
        {
            content: "Open the filter menu",
            trigger: "#portal_searchbar_filters",
            run: "click",
        },
        {
            content: `Keep the ${filter} orders only`,
            trigger: `div[aria-labelledby='portal_searchbar_filters'] .dropdown-item[href*='filterby=${filter}']`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
}
