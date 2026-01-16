export function isTabActive(tabText) {
    return [
        {
            content: "Check if the active tab contains the text" + tabText,
            trigger: `.pos-leftheader span.text-bg-info:contains(${tabText})`,
        },
    ];
}

export function closePrintingWarning() {
    return [
        {
            trigger: `.modal:has(.modal-header:contains(printing failed)) .modal-footer .btn-primary:contains(continue)`,
            content: "acknowledge printing error ( because we don't have printer in the test. )",
            run: "click",
            timeout: 30000,
        },
    ];
}
