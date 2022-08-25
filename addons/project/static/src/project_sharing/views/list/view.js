/** @odoo-module **/

import ListView from 'web.ListView';
import Controller from './controller';

export default ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller,
    }),

    init: function (viewInfo, params) {
        return this._super(viewInfo, {...params, hasSelectors: false});
    },
    getRenderer (parent, state) {
        const columnInvisibleFields = {};
        for (const child of this.arch.children) {
            if (child.attrs && child.attrs.modifiers && child.attrs.modifiers.column_invisible) {
                columnInvisibleFields[child.attrs.name] = child.attrs.modifiers.column_invisible;
            }
        }
        this.rendererParams.columnInvisibleFields = Object.entries(columnInvisibleFields).reduce((acc, entry) => {
            const [fieldName, domains] = entry;
            if (domains instanceof Array && state.data.length) {
                const record = state.data[0];
                const data = Object.entries(record.data).reduce((acc, entry) => {
                    const [fieldName, value] = entry;
                    const field = record.fields[fieldName];
                    if (field.type === 'one2many' || field.type === 'many2many') {
                        if (value instanceof Object && value.type === 'list') {
                            acc[fieldName] = value.id;
                        }
                    }
                    return acc;
                }, record.data);
                if (Object.keys(data).length) {
                    // We assume the field in this domain is a related to the project shared.
                    acc[fieldName] = this.model._evalModifiers({ ...record, data }, { column_invisible: domains }).column_invisible;
                }
            } else {
                acc[fieldName] = domains;
            }
            return acc;
        }, {});
        return this._super(parent, state);
    },
});
