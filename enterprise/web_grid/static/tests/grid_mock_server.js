import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("grid_update_cell", function gridUpdateCell({ args, kwargs, model }) {
    const [domain, fieldNameToUpdate, value] = args;
    const records = this.env[model].search_read(domain, [fieldNameToUpdate], kwargs);
    if (records.length > 1) {
        this.env[model].copy(records[0].id, { [fieldNameToUpdate]: value });
    } else if (records.length === 1) {
        const record = records[0];
        this.env[model].write(record.id, {
            [fieldNameToUpdate]: record[fieldNameToUpdate] + value,
        });
    } else {
        this.env[model].create({ [fieldNameToUpdate]: value }, kwargs);
    }
    return false;
});
