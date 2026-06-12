import { ActivityCompiler } from "@mail/views/web/activity/activity_compiler";

import { Component, props, types } from "@odoo/owl";

import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { isHtmlEmpty } from "@web/core/utils/html";
import { Field } from "@web/views/fields/field";
import { getFormattedRecord, getImageSrcFromRecordInfo } from "@web/views/kanban/kanban_record";
import { useViewCompiler } from "@web/views/view_compiler";
import { Record } from "@web/model/relational_model/record";

export class ActivityRecord extends Component {
    static components = {
        Field,
    };
    static template = "mail.ActivityRecord";

    setup() {
        this.props = props({
            archInfo: types.object(),
            openRecord: types.function([
                types.instanceOf(Record),
                types.object({ "newWindow?": types.boolean() }),
            ]),
            record: types.instanceOf(Record),
        });
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
