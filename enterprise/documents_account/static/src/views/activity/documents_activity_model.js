import { DocumentsActivityModel } from "@documents/views/activity/documents_activity_model";
import { patch } from "@web/core/utils/patch";
import { AccountIsViewablePatch } from "../documents_model_mixin";

patch(DocumentsActivityModel.Record.prototype, AccountIsViewablePatch);
