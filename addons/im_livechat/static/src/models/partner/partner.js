/** @odoo-module **/

let nextPublicId = -1;

export const classPatchPartner = {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    getNextPublicId() {
        const id = nextPublicId;
        nextPublicId -= 1;
        return id;
    },
};
