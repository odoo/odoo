export function isTabActive(tabText) {
    return [
        {
            content: "Check if the active tab contains the text" + tabText,
            trigger: `.pos-leftheader span.bg-info-subtle:contains(${tabText})`,
        },
    ];
}
