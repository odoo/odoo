/** @odoo-module */

import ListRenderer from 'web.ListRenderer';

export default ListRenderer.extend({
    updateState(state, params) {
        // populate the columnInvisibleFields in params to compute the domain in column_invisible
        const columnInvisibleFields = params.columnInvisibleFields || {};
        const model = this.getParent().model;
        const record = state.data[0];
        const data = Object.entries(record.data).reduce((acc, entry) => {
            const [fieldName, value] = entry;
            const field = record.fields[fieldName];
            if (['one2many', 'many2many'].includes(field.type)) {
                if (value instanceof Object && value.type === 'list') {
                    acc[fieldName] = value.id;
                }
            }
            return acc;
        }, record.data);
        if (Object.keys(data).length) {
            for (const node of this.arch.children) {
                if (node.tag === 'field' && node.attrs.modifiers.column_invisible instanceof Array) {
                    columnInvisibleFields[node.attrs.name] = model._evalModifiers({ ...record, data }, { column_invisible: node.attrs.modifiers.column_invisible }).column_invisible;
                }
            }
        }
        return this._super(
            state,
            Object.assign({}, params, {
                columnInvisibleFields,
            }),
        );
    }
});
