import { Component, t, useProps } from "@odoo/owl";
import { useModel } from "@web/model/model";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { standardViewProps } from "@web/views/standard_view_props";

export class ListController extends Component {
    static template = "web.next.ListController";
    static components = { Layout };

    props = useProps({
        ...standardViewProps,
        Model: t.function(),
        Renderer: t.function(),
        /** @type {any} field nodes, see `FieldNode` */
        columns: t.array(),
        specification: t.object(),
    });

    model = useModel(this.props.Model, {
        resModel: this.props.resModel,
        specification: this.props.specification,
        relatedModels: this.props.relatedModels,
        limit: this.props.limit,
    });

    setup() {
        usePager(() => ({
            offset: this.model.offset(),
            limit: this.model.limit(),
            total: this.model.count(),
            onUpdate: ({ offset, limit }) => this.model.loadPage(offset, limit),
        }));
    }

    /**
     * Opens a record in the form view of the action, with the records of the
     * page to navigate.
     *
     * @param {any} record a record of the store
     */
    openRecord(record) {
        const activeIds = this.model.records().map((rec) => rec.id);
        this.props.selectRecord(record.id, { activeIds });
    }
}
