import { DynamicPlaceholderPopover } from "@web/views/fields/dynamic_placeholder_popover";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";

class EditorModelFieldSelectorPopover extends ModelFieldSelectorPopover {
    // When clicking on a field of which we can follow relation, if it has a
    // name field in its subfields, we return the name by default.
    async selectFieldDisplayname(fieldDef) {
        const { modelsInfo } = await this.keepLast.add(
            this.fieldService.loadPath(
                fieldDef.is_property ? fieldDef.relation : this.state.page.resModel,
                `${fieldDef.name}.*`
            )
        );
        const { fieldDefs } = modelsInfo.at(-1);
        const fieldName = "name" in fieldDefs ? `${fieldDef.name}.name` : fieldDef.name;
        const fieldData = "name" in fieldDefs ? fieldDefs.name : fieldDef;
        return [fieldName, fieldData];
    }

    async selectField(field) {
        if (field.type === "properties") {
            return this.followRelation(field);
        }
        const [fieldName, fieldData] = this.canFollowRelationFor(field)
            ? await this.selectFieldDisplayname(field)
            : [field.name, field];
        this.keepLast.add(Promise.resolve());
        this.state.page.selectedName = fieldName;
        this.props.update(this.state.page.path, fieldData);
        this.props.close(true);
    }
}

export class EditorDynamicPlaceholderPopover extends DynamicPlaceholderPopover {
    static template = "html_editor.EditorDynamicPlaceholderPopover";
    static components = {
        EditorModelFieldSelectorPopover,
    };
}
