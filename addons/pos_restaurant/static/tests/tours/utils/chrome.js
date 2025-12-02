import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

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
            ...Dialog.confirm(),
            content: "acknowledge printing error ( because we don't have printer in the test. )",
        },
    ];
}
