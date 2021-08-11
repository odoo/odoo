/** @odoo-module **/
import { registry } from "@web/core/registry";
import { getX2MViewModes } from "../views/helpers/view_utils";
import { KanbanRenderer } from "../views/kanban/kanban_renderer";
import { KanbanArchParser } from "../views/kanban/kanban_view";
import { ListRenderer } from "../views/list/list_renderer";
import { ListArchParser } from "../views/list/list_view";

const { Component } = owl;
const fieldRegistry = registry.category("fields");

const X2M_RENDERERS = {
    list: [ListRenderer, ListArchParser],
    kanban: [KanbanRenderer, KanbanArchParser],
};

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
        // To remove when we can discriminate between in list view or in formView
        // Also, make a loadViews if archs is passed but not set
        if ("archs" in this.props) {
            const viewModes = this.props.viewMode || ["tree"];
            const { arch, fields } = this.props.archs[viewModes[0]] || {};
            if (!arch) {
                return;
            }
            this.fields = fields;
            this.record = this.props.record.data[this.props.name];

            const [viewMode] = getX2MViewModes(viewModes);
            if (viewMode in X2M_RENDERERS) {
                const [Renderer, Parser] = X2M_RENDERERS[viewMode];
                this.archInfo = new Parser().parse(arch, fields);
                this.Renderer = Renderer;
            }
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
