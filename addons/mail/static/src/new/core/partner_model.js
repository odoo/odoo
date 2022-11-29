/** @odoo-module */

export class Partner {
    static insert(state, data) {
        if (data.id in state.partners) {
            return state.partners[data.id];
        }
        let partner = new Partner(data);
        state.partners[data.id] = partner;
        // return reactive version
        partner = state.partners[data.id];
        if (
            partner.im_status !== "im_partner" &&
            !partner.is_public &&
            !state.registeredImStatusPartners.includes(partner.id)
        ) {
            state.registeredImStatusPartners.push(partner.id);
        }
        // return reactive version
        return partner;
    }

    constructor({ id, name }) {
        Object.assign(this, { id, name, im_status: null });
    }
}
