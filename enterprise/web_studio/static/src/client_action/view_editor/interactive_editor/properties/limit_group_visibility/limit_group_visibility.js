/** @odoo-module */

import { Component, onWillRender } from "@odoo/owl";
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
        onWillRender(() => {
            const groups = JSON.parse(this.props.node.attrs.studio_groups || "[]");
            this.allowGroups = [];
            this.forbidGroups = [];
            this.currentGroups = [];
            for (const group of groups) {
                const groupId = group.id;
                this.currentGroups.push(groupId);
                if (group.forbid) {
                    this.forbidGroups.push(groupId);
                } else {
                    this.allowGroups.push(groupId);
                }
            }
        })
    }

    handleNodeGroupsChange(allow, forbid) {
        allow = new Set(allow || this.allowGroups);
        forbid = new Set(forbid || this.forbidGroups);
        if (!allow.isDisjointFrom(forbid)) {
            throw new Error("Cannot allow and forbid at the same time");
        }
        const resIds = [];
        for (const g of allow) {
            resIds.push(g);
        }
        for (const g of forbid) {
            resIds.push(`!${g}`)
        }
        return this.editNodeAttributes({ groups: resIds });
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }

    get allowGroupsProps() {
        return {
            resModel: "res.groups",
            domain: [["id", "not in", this.currentGroups]],
            resIds: this.allowGroups,
            update: (resIds) => this.handleNodeGroupsChange(resIds, null),
        };
    }

    get forbidGroupsProps() {
        return {
            resModel: "res.groups",
            domain: [["id", "not in", this.currentGroups]],
            resIds: this.forbidGroups,
            update: (resIds) => this.handleNodeGroupsChange(null, resIds),
        };
    }
}
