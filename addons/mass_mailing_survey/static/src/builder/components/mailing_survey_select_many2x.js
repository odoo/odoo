import { SelectMany2X } from "@html_builder/core/building_blocks/select_many2x";
import { patch } from "@web/core/utils/patch";

patch(SelectMany2X.prototype, {
    getSearchFields() {
        const fields = super.getSearchFields();
        if (this.props.model === "survey.survey") {
            fields.splice(fields.indexOf("name"), 1);
        }
        return fields;
    },
});
