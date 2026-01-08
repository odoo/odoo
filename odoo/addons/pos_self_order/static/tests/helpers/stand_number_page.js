/** @odoo-module */

export function selectStandNumber(tableStand) {
    return [
        {
            content: `Select table stand ${tableStand}`,
            trigger: `.numpad .touch-key:contains("${tableStand}")`,
        },
        {
            content: `Click on 'Pay' button`,
            trigger: `.btn:contains('Pay')`,
        },
    ];
}
