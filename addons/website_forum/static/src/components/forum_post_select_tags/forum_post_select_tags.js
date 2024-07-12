/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class ForumPostSelectMenu extends SelectMenu {
    static template = "website_forum.ForumPostSelectMenu";
    static props = {
        ...super.props,
        getErrorMessage: { type: Function },
        hasTokenSeparator: { type: Boolean },
    };

    setup() {
        super.setup();
        this.debouncedOnInput = useDebounced(
            () => this.onInput(this.inputRef.el ? this.inputRef.el.value : ""),
            250
        );
        onWillUpdateProps((nextProps) => {
            if (nextProps.hasTokenSeparator) {
                this.inputRef.el.value = "";
                this.state.searchValue = "";
            }
        });
    }
}

registry
    .category("public_components")
    .add("website_forum.ForumPostSelectMenu", ForumPostSelectMenu);

export class ForumPostSelectTags extends Component {
    static components = { DropdownItem, ForumPostSelectMenu };
    static defaultProps = {
        maximumInputLength: 35,
        minimumInputLength: 2,
        maximumSelectionSize: 5,
        tokenSeparators: [",", " ", "_"],
    };
    static props = {
        forumId: { type: Number },
        initValue: { type: String | null, optional: true },
        karma: { type: Number },
        karmaEditRetag: { type: Number },
        maximumInputLength: { type: Number, optional: true },
        minimumInputLength: { type: Number, optional: true },
        maximumSelectionSize: { type: Number, optional: true },
        tokenSeparators: { type: Array, optional: true },
    };
    static template = "website_forum.ForumPostSelectTags";

    setup() {
        this.createdTags = [];
        this.orm = useService("orm");
        this.state = useState({
            value: [],
            choices: [],
            hasTokenSeparator: false,
        });
        this.token = "";

        onWillStart(async () => {
            if (this.props.initValue) {
                this.state.value = JSON.parse(this.props.initValue).map((choice) => {
                    return choice.id;
                });
            }
            this.getForumTags();
        });
    }

    getErrorMessage(input) {
        if (this.props.karma < this.props.karmaEditRetag) {
            return _t("You need to have sufficient karma to edit tags");
        }
        if (this.state.value.length >= this.props.maximumSelectionSize) {
            return _t("You can only select %s items", this.props.maximumSelectionSize);
        }
        if (input.length < this.props.minimumInputLength) {
            return _t("Please enter at least %s characters", this.props.minimumInputLength);
        }
        if (input.length >= this.props.maximumInputLength) {
            return _t("Please enter at most %s characters", this.props.maximumInputLength);
        }
        return "";
    }

    async getForumTags() {
        const results = await this.orm.call("forum.tag", "search_read", [], {
            domain: [["forum_id", "=", this.props.forumId]],
            fields: ["id", "name"],
        });

        this.state.choices = results.map((choice) => {
            return { value: choice.id, label: choice.name };
        });
    }

    onInput(searchString) {
        this.state.hasTokenSeparator = false;
        this.token = searchString.split(new RegExp(this.props.tokenSeparators.join("|")))[0];

        if (this.token !== searchString) {
            const label = this.token.trim();
            const tag = this.state.choices.find(
                (choice) => choice.label.toLowerCase() === label.toLowerCase()
            );

            if (tag) {
                this.onTagsSelect([...this.state.value, tag.value]);
            } else if (this.canCreateTag(label, this.state.choices)) {
                this.onClickCreateTagBtn(label);
            }
            this.state.hasTokenSeparator = true;
        }
    }

    onTagsSelect(values) {
        this.state.value = values;
    }

    onClickCreateTagBtn(tagName) {
        const newTag = tagName.trim();
        this.state.choices = [...this.state.choices, { value: `_${newTag}`, label: newTag }];
        this.state.value = [...this.state.value, `_${newTag}`];
    }

    /**
     * To figure when to propose/allow users to create a new category or tag:
     * users need to have the required level of karma
     * input length should be comprised between a min and a max number of characters
     * input should not match any existing choice
     * current selection should not exceed the limit number of tags
     */
    canCreateTag(input, choices) {
        return (
            this.props.karma >= this.props.karmaEditRetag &&
            input.length >= this.props.minimumInputLength &&
            input.length < this.props.maximumInputLength &&
            this.state.value.length < this.props.maximumSelectionSize &&
            !choices.some((choice) => input.toLowerCase() === choice.label.toLowerCase())
        );
    }
}

registry
    .category("public_components")
    .add("website_forum.ForumPostSelectTags", ForumPostSelectTags);
