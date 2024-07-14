/** @odoo-module **/

import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { DocumentsModelMixin, DocumentsRecordMixin } from "../documents_model_mixin";

export class DocumentsActivityModel extends DocumentsModelMixin(ActivityModel) {}

DocumentsActivityModel.Record = class DocumentsActivityRecord extends DocumentsRecordMixin(ActivityModel.Record) {};

