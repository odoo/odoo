import { registry } from "@web/core/registry";
import { booleanFavoriteField } from "@web/views/fields/boolean_favorite/boolean_favorite_field";

export const projectIsFavoriteField = {
    ...booleanFavoriteField,
    extractProps: (fieldsInfo, dynamicInfo) => {
        return {
            ...booleanFavoriteField.extractProps(fieldsInfo, dynamicInfo),
            readonly: Boolean(fieldsInfo.attrs.readonly),
        };
    },
};

registry.category("fields").add("project_is_favorite", projectIsFavoriteField);
