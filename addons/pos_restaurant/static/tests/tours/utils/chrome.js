export function isTabActive(tabText) {
    return [
        {
            content: "Check if the active tab contains the text" + tabText,
            trigger: `.navbar-menu .btn-primary:contains(${tabText})`,
        },
    ];
}

export function activeTableOrOrderIs(label) {
    return {
        trigger: `.table-free-order-label:contains("${label}")`,
    };
}
