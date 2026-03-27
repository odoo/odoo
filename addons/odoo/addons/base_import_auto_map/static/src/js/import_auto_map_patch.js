/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ImportDataContent } from "@base_import/import_data_content/import_data_content";
import { ImportDataSidepanel } from "@base_import/import_data_sidepanel/import_data_sidepanel";

function getFirstFieldInfo(column) {
    if (!column || !column.fields) {
        return null;
    }
    const lists = ["basic", "suggested", "additional", "relational"];
    for (const name of lists) {
        const items = column.fields[name] || [];
        if (items.length) {
            return items[0];
        }
    }
    return null;
}

patch(ImportDataContent.prototype, {
    setup() {
        super.setup(...arguments);

        const autoAssign = () => {
            const columns = this.props?.columns || [];
            for (const column of columns) {
                if (column.fieldInfo) {
                    continue;
                }
                const fieldInfo = getFirstFieldInfo(column);
                if (fieldInfo) {
                    this.props.onFieldChanged(column, fieldInfo);
                }
            }
        };

        onMounted(() => autoAssign());
        onPatched(() => autoAssign());
    },

    onFieldChanged() {
        return;
    },
});

patch(ImportDataSidepanel.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if (!this.props.options.has_headers) {
                this.props.onOptionChanged("has_headers", true);
            }
        });
    },

    setOptionValue(name, value) {
        if (name === "has_headers") {
            return super.setOptionValue(name, true);
        }
        return super.setOptionValue(name, value);
    },
});
