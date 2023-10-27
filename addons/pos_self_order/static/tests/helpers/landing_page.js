/** @odoo-module */

export function selectLocation(locationName) {
    return {
        content: `Click on location '${locationName}'`,
        trigger: `.o_kiosk_eating_location_box h3:contains('${locationName}')`,
    };
}

export function isClosed() {
    return {
        content: `Check if the POS is closed`,
        trigger: `.o-self-closed`,
        run: () => {},
    };
}
