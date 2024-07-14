/** @odoo-module */

import { archParseBoolean } from "@web/views/utils";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { getRandomIcon } from "@knowledge/js/knowledge_utils";

import { Component, useRef } from "@odoo/owl";

export default class KnowledgeIcon extends Component {
    static template = "knowledge.KnowledgeIcon";
    static props = {
        record: Object,
        readonly: Boolean,
        iconClasses: {type: String, optional: true},
        allowRandomIconSelection: {type: Boolean, optional: true},
        autoSave: {type: Boolean, optional: true},
    };

    setup() {
        super.setup();
        this.iconRef = useRef("icon");
        this.emojiPicker = useEmojiPicker(this.iconRef, { hasRemoveFeature: true, onSelect: this.updateIcon.bind(this) });
    }

    get icon() {
        return this.props.record.data.icon;
    }

    async selectRandomIcon() {
        this.updateIcon(await getRandomIcon());
    }

    updateIcon(icon) {
        this.props.record.update({icon});
        if (this.props.autoSave) {
            this.props.record.save();
        }
    }
}

class KnowledgeIconField extends KnowledgeIcon {
    static props = {
        ...standardFieldProps,
        allowRandomIconSelection: Boolean,
        autoSave: Boolean,
    };
}

registry.category("fields").add("knowledge_icon", {
    component: KnowledgeIconField,
    extractProps({ attrs, viewType }, dynamicInfo) {
        return {
            autoSave: viewType === "kanban",
            readonly: dynamicInfo.readonly,
            allowRandomIconSelection: archParseBoolean(attrs.allow_random_icon_selection),
        };
    },
});
