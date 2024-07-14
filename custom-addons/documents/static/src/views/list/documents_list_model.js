/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { DocumentsModelMixin, DocumentsRecordMixin } from "../documents_model_mixin";

const ListModel = listView.Model;
export class DocumentsListModel extends DocumentsModelMixin(ListModel) {}

DocumentsListModel.Record = class DocumentsListRecord extends DocumentsRecordMixin(ListModel.Record) {};
