/**  @odoo-module */

export function isValidEmail(val) {
    // http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
    const re =
        /^(([^<>()[\].,;:\s@"]+(\.[^<>()[\].,;:\s@"]+)*)|(".+"))@(([^<>()[\].,;:\s@"]+\.)+[^<>()[\].,;:\s@"]{2,})$/i;
    return re.test(val);
}
