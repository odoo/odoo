import { registry } from "@web/core/registry";
import { booleanFavoriteField } from "@web/views/fields/boolean_favorite/boolean_favorite_field";

export const lunchIsFavoriteField = {
    ...booleanFavoriteField,
    extractProps: (fieldsInfo, dynamicInfo) => {
        return {
            ...booleanFavoriteField.extractProps(fieldsInfo, dynamicInfo),
            readonly: Boolean(fieldsInfo.attrs.readonly),
        };
    },
};

registry.category("fields").add("lunch_is_favorite", lunchIsFavoriteField);
