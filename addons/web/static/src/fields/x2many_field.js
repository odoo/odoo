/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

export class X2ManyField extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.fieldInfo = this.props.record.activeFields[this.props.name];
        // should we readd protection on this.fieldInfo.views?
        // in rendererProps also then?
        this.Renderer = X2M_RENDERERS[this.fieldInfo.viewMode];
        this.viewMode = this.fieldInfo.viewMode;
    }

    get rendererProps() {
        const subViewInfo = this.fieldInfo.views[this.viewMode];
        return {
            creates: this.creates,
            info: {
                ...subViewInfo,
                editable: this.props.record.isInEdition && subViewInfo.editable,
            },
            fields: Object.assign({}, this.props.fields, subViewInfo.fields), // WOWL is this necessary?
            list: this.props.value,
            openRecord: this.openRecord.bind(this),
            hasTrashIcon: this.viewMode === "list",
        };
    }

    get creates() {
        if (this.viewMode !== "list") {
            return null;
        }
        const { data } = this.props.record;
        const { options } = this.fieldInfo;
        const subViewInfo = this.fieldInfo.views[this.viewMode];
        // WOWL something of that taste?
        const canCreate = "create" in options ? new Domain(options.create).contains(data) : true;
        const canDelete = "delete" in options ? new Domain(options.delete).contains(data) : true;
        const canLink = "link" in options ? new Domain(options.link).contains(data) : true;
        const canUnlink = "unlink" in options ? new Domain(options.unlink).contains(data) : true;

        const create = canCreate && subViewInfo.creates.create;
        const unlink = canUnlink;
        return { create, canDelete, canLink, unlink };
    }

    get pagerProps() {
        const list = this.props.value;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                list.offset = offset;
                list.limit = limit;
                await list.load();
                this.render();
            },
            withAccessKey: false,
        };
    }

    openRecord(record) {
        this.dialogService.add(FormViewDialog, {
            archInfo: this.props.value.views.form, // FIXME: might not be there
            record,
            readonly: this.props.readonly,
            title: this.props.record.activeFields[this.props.name].string,
        });
    }
}

X2ManyField.useSubView = true;
X2ManyField.components = { Pager };
X2ManyField.props = { ...standardFieldProps };
X2ManyField.template = "web.X2ManyField";

registry.category("fields").add("one2many", X2ManyField);
registry.category("fields").add("many2many", X2ManyField);
