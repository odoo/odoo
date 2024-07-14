/** @odoo-module */

import { Component } from "@odoo/owl";
import { Record } from "@web/model/record";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

export class LimitGroupVisibility extends Component {
    static template = "web_studio.ViewEditor.LimitGroupVisibility";
    static components = {
        Record,
        MultiRecordSelector,
    };
    static props = {
        node: { type: Object },
    };

    setup() {
        this.editNodeAttributes = useEditNodeAttributes();
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }

    get multiRecordSelectorProps() {
        const resIds = JSON.parse(this.props.node.attrs.studio_groups || "[]").map(
            (group) => group.id
        );
        return {
            resModel: "res.groups",
            resIds,
            update: (resIds) => {
                this.onChangeAttribute(resIds, "groups");
            },
        };
    }
}
