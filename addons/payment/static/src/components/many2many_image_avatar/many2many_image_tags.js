import {
    Many2ManyTagsAvatarField,
    many2ManyTagsAvatarField,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import {imageUrl} from "@web/core/utils/urls";
import {registry} from "@web/core/registry";

export class Many2ManyImageTags extends Many2ManyTagsAvatarField {

    static defaultProps = {
        ...Many2ManyTagsAvatarField.defaultProps,
        tagLimit: 10,
    };

    getTagProps(record) {
        const props = super.getTagProps(record);
        props.imageUrl = imageUrl(this.relation, record.resId, "image");
        props.text = '';
        return props;
    }
}

export const many2ManyImageTags = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyImageTags,
    additionalClasses: ["o_field_many2many_tags"]
};

registry.category("fields").add("many2many_image_tags", many2ManyImageTags);
