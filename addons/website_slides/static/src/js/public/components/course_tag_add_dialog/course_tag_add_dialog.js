/** @odoo-module native */
import { Component, useState } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown";
import { SelectMenu } from "@web/components/select_menu";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { uniqueId } from "@web/core/utils/functions";
import { Dialog } from "@web/ui/dialog";

export class CourseTagAddDialog extends Component {
    static components = { Dialog, DropdownItem, SelectMenu };
    static props = {
        channelId: { type: Number, optional: true },
        defaultTag: { type: String, optional: true },
        tagIds: Array,
        close: Function,
    };
    static template = "website_slides.CourseTagAddDialog";

    async setup() {
        super.setup();
        this.choices = useState({
            tagIds: [],
            tagGroupIds: [],
            tagId: null,
            tagGroupId: null,
        });
        this.state = useState({
            showTagGroup: false,
            canCreateTagGroup: false,
            canCreateTag: false,
            alertMsg: "",
        });
        this.validation = useState({
            tagIsValid: undefined,
            tagGroupIsValid: undefined,
        });
        const [tags, groups] = await Promise.all([
            this._fetchChoices("tag", [
                ["id", "not in", this.props.tagIds],
                ["color", "!=", 0],
            ]),
            this._fetchChoices("tag/group"),
        ]);
        this.choices.tagIds = tags.choices;
        this.state.canCreateTag = tags.can_create;
        this.choices.tagGroupIds = groups.choices;
        this.state.canCreateTagGroup = groups.can_create;

        if (this.props.defaultTag) {
            this.createChoice(this.props.defaultTag);
            this.state.canCreateTag = false;
        }
    }

    get displayTagValue() {
        return this.choices.tagId
            ? this.choices.tagIds.find((t) => t.value === this.choices.tagId).label
            : _t("Select or create a tag");
    }

    get displayTagGroupValue() {
        return this.choices.tagGroupId
            ? this.choices.tagGroupIds.find((t) => t.value === this.choices.tagGroupId)
                  .label
            : _t("Select or create a tag group");
    }

    onClickFormSubmit() {
        this.state.alertMsg = "";
        if (!this._formValidate()) {
            return;
        }
        const values = this._getSelectMenuValues();
        if (this.props.defaultTag && !this.props.channelId) {
            this._createNewTag(values);
        } else {
            this._addTagToChannel(values);
        }
    }

    /**
     * @param {String} label
     * @param {String} type
     */
    createChoice(label, type = "tag") {
        const tempId = uniqueId("temp");
        this.choices[`${type}Ids`].push({ value: tempId, label: label });
        this.choices[`${type}Id`] = tempId;
        this.state.showTagGroup = true;
    }

    /**
     * @param {*} value
     */
    onTagSelect(value) {
        if (!this.props.defaultTag) {
            this.choices.tagId = value;
            this.state.showTagGroup = this._toCreate(value) ? true : false;
        }
    }

    /**
     * @param {*} value
     */
    onTagGroupSelect(value) {
        this.choices.tagGroupId = value;
    }

    /**
     * @private
     * @param {Object} values
     */
    async _addTagToChannel(values) {
        const data = await rpc("/slides/channel/tag/add", {
            channel_id: this.props.channelId,
            ...values,
        });

        if (data.error) {
            this.state.alertMsg = data.error;
        } else {
            window.location.reload();
        }
    }

    /**
     * @private
     * @param {Object} values
     */
    async _createNewTag(values) {
        const data = await rpc("/slide_channel_tag/add", values);

        if (data.error) {
            this.state.alertMsg = data.error;
        } else {
            this.props.close();
        }
    }

    /**
     * @private
     */
    _formValidate() {
        for (const key in this.validation) {
            this.validation[key] = undefined;
        }
        if (!this.choices.tagId) {
            this.validation.tagIsValid = false;
            return false;
        }
        this.validation.tagIsValid = true;
        if (this.state.showTagGroup) {
            if (!this.choices.tagGroupId) {
                this.validation.tagGroupIsValid = false;
                return false;
            }
            this.validation.tagGroupIsValid = true;
        }
        return true;
    }

    /**
     * @private
     * @param {String} type
     * @param {Array} domain
     * @param {Array} fields
     * @returns {Object}
     */
    async _fetchChoices(type, domain = [], fields = ["name"]) {
        const { read_results, can_create } = await rpc(
            `/slides/channel/${type}/search_read`,
            {
                fields,
                domain,
            },
        );

        const choices = read_results.map((choice) => ({
            value: choice.id,
            label: choice.name,
        }));
        return { choices, can_create };
    }

    /**
     * @private
     */
    _getSelectMenuValues() {
        const tag = this.choices.tagIds.find((c) => c.value === this.choices.tagId);
        if (!tag) {
            return {};
        }
        if (!this._toCreate(tag.value)) {
            return { tag_id: [tag.value] };
        }
        const group = this.choices.tagGroupIds.find(
            (c) => c.value === this.choices.tagGroupId,
        );
        if (!group) {
            return {};
        }
        return {
            tag_id: [0, { name: tag.label }],
            group_id: this._toCreate(group.value)
                ? [0, { name: group.label }]
                : [group.value],
        };
    }

    /**
     * @private
     * @param {*} value
     */
    _toCreate(value) {
        return typeof value === "string" && value.startsWith("temp");
    }
}
