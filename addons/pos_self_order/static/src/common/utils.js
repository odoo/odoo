/** @odoo-module */

export const categorySorter = (a, b, start_categ_id) => {
    if (a.id === start_categ_id && b.id !== start_categ_id) {
        return -1; // 'a' should come before 'b'
    }
    if (a.id !== start_categ_id && b.id === start_categ_id) {
        return 1; // 'b' should come before 'a'
    }
    if (a.sequence !== b.sequence) {
        return a.sequence - b.sequence; // sort by sequence
    }
    return a.id - b.id; // sort by id if sequences are the same
};
