export function checkCustomerNotes(note) {
    return [
        {
            content: `check customer notes`,
            trigger: `.customer-note:contains(${note})`,
        },
    ];
}
