import { ActivityCompiler } from "@mail/views/web/activity/activity_compiler";

import { Component } from "@odoo/owl";

import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { isHtmlEmpty } from "@web/core/utils/html";
import { Field } from "@web/views/fields/field";
import { getFormattedRecord, getImageSrcFromRecordInfo } from "@web/views/kanban/kanban_record";
import { useViewCompiler } from "@web/views/view_compiler";

export class ActivityRecord extends Component {
    static components = {
        Field,
    };
    static props = {
        archInfo: { type: Object },
        openRecord: { type: Function },
        record: { type: Object },
    };
    static template = "mail.ActivityRecord";

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.widget = {
            deletable: false,
            editable: false,
            isHtmlEmpty,
        };
        const { templateDocs } = this.props.archInfo;
        const templates = useViewCompiler(ActivityCompiler, templateDocs);
        this.recordTemplate = templates["activity-box"];
    }

    getRenderingContext() {
        const { record } = this.props;
        return {
            record: getFormattedRecord(record),
            activity_image: (...args) => getImageSrcFromRecordInfo(record, ...args),
            user_context: user.context,
            widget: this.widget,
            luxon,
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
    }
}
