import { DynamicPlaceholderPopover } from "@web/views/fields/dynamic_placeholder_popover";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";

class EditorModelFieldSelectorPopover extends ModelFieldSelectorPopover {
    // When clicking on a field of which we can follow relation, we return the
    // display name by default.
    async selectFieldDisplayname(fieldDef) {
        const { modelsInfo } = await this.keepLast.add(
            this.fieldService.loadPath(
                fieldDef.is_property ? fieldDef.relation : this.state.page.resModel,
                `${fieldDef.name}.*`
            )
        );
        const { fieldDefs } = modelsInfo.at(-1);
        const fieldName = `${fieldDef.name}.display_name`;
        const fieldData = fieldDefs.display_name;
        this.state.label = fieldDef.string;
        return [fieldName, fieldData];
    }

    async selectField(field) {
        if (field.type === "properties") {
            return this.followRelation(field);
        }
        this.state.isFollowable = this.canFollowRelationFor(field);
        const [fieldName, fieldData] = this.state.isFollowable
            ? await this.selectFieldDisplayname(field)
            : [field.name, field];
        this.keepLast.add(Promise.resolve());
        this.state.page.selectedName = fieldName;
        if (this.state.isFollowable) {
            this.props.update(this.state.page.path, fieldData, this.state.label);
        } else {
            this.props.update(this.state.page.path, fieldData);
        }
        this.props.close(true);
    }
}

export class EditorDynamicPlaceholderPopover extends DynamicPlaceholderPopover {
    static template = "html_editor.EditorDynamicPlaceholderPopover";
    static components = {
        EditorModelFieldSelectorPopover,
    };
    setPath(path, fieldInfo, forceLabel = null) {
        this.state.path = path;
        this.state.fieldName = forceLabel || fieldInfo?.string;
        this.fieldType = fieldInfo?.type;
    }
}
