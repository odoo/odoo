/** @odoo-module **/
import { registry } from "@web/core/registry";
import { ListRenderer } from "../views/list/list_renderer";
import { ListArchParser } from "../views/list/list_view";

const { Component } = owl;
const fieldRegistry = registry.category("fields");

export class FieldMany2one extends Component {
    setup() {
        const data = this.props.record.data[this.props.name];
        this.data = data ? data[1] : "";
    }
}

FieldMany2one.template = "web.FieldMany2one";

fieldRegistry.add("many2one", FieldMany2one);

export class FieldMany2ManyTags extends Component {
    setup() {
        const dataList = this.props.record.data[this.props.name];
        this.data = (dataList && dataList.data) || [];
    }
}

FieldMany2ManyTags.template = "web.FieldMany2ManyTags";
FieldMany2ManyTags.fieldsToFetch = ["display_name"];

fieldRegistry.add("many2many_tags", FieldMany2ManyTags);

export class FieldKanbanMany2ManyTags extends FieldMany2ManyTags {}

FieldKanbanMany2ManyTags.template = "web.FieldKanbanMany2ManyTags";

fieldRegistry.add("kanban.many2many_tags", FieldKanbanMany2ManyTags);

export class FieldX2Many extends Component {
    setup() {
        const viewMode = this.props.viewMode || ["list"];
        // To remove when we can discriminate between in list view or in formView
        // Also, make a loadViews if archs is passed but not set
        if ("archs" in this.props) {
            const { arch, fields } = this.props.archs[viewMode[0]] || {};
            if (!arch) {
                return;
            }
            this.fields = fields;
            this.record = this.props.record.data[this.props.name];

            this.archInfo = new ListArchParser().parse(arch, fields);
            this.Renderer = ListRenderer;
        }
    }

    openRecord(record) {
        console.log("FieldX2M openRecord", record);
    }
}
FieldX2Many.useSubView = true;

FieldX2Many.template = "web.FieldX2Many";

fieldRegistry.add("one2many", FieldX2Many);
fieldRegistry.add("many2many", FieldX2Many);
