export function isTabActive(tabText) {
    return [
        {
            content: "Check if the active tab contains the text" + tabText,
            trigger: `.pos-leftheader span.bg-info-subtle:contains(${tabText})`,
        },
    ];
}

export function closePrintingWarning() {
    return [
        {
            content: "acknowledge printing error ( because we don't have printer in the test. )",
            trigger: `.modal:has(.modal-header:contains(printing failed)) .modal-footer .btn-primary:contains(continue)`,
            run: "click",
            timeout: 15000,
        },
    ];
}
