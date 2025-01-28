import { Component, useState, onWillStart } from "@odoo/owl";
import { get } from "@web/core/network/http_service";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class WebsiteForumTagsWrapper extends Component {
    static template = "website_forum.WebsiteForumTagsWrapper";
    static components = { SelectMenu, DropdownItem };
    static defaultProps = {
        isReadOnly: false,
    };
    static props = {
        defaulValue: { optional: true, type: Array },
        isReadOnly: { optional: true, Type: Boolean },
    };

    setup() {
        this.state = useState({
            value: this.props.defaulValue || [],
        });
        onWillStart(async () => {
            await this.loadChoices();
        });
    }

    get showCreateOption() {
        // The "Create" option should not be visible if:
        // 1. Tag length is less than 2.
        // 2. The tag already exists (tags are created on form submission, so
        // consider the current value).
        // 3. There is insufficient karma.
        const searchValue = this.select.data.searchValue;
        const karma = document.querySelector("#karma").value;
        const editKarma = document.querySelector("#karma_edit_retag").value;
        const hasEnoughKarma = parseInt(karma) >= parseInt(editKarma);

        return hasEnoughKarma && searchValue.length >= 2
            && !this.state.choices.some(c => c.label === searchValue)
            && !this.state.value.some(v => v === `_${searchValue.trim()}`);
    }

    onCreateOption(string) {
        const choice = {
            label: string.trim(),
            value: `_${string.trim()}`,
        };
        this.state.choices.push(choice);
        this.onSelect([...this.state.value, choice.value]);
    }

    onSelect(values) {
        this.state.value = values;
    }

    async loadChoices(searchString = "") {
        const forumID = document.querySelector("#wrapwrap").dataset.forum_id;
        const choices = await new Promise((resolve, reject) => {
            get(`/forum/get_tags?query=${searchString}&limit=${50}&forum_id=${forumID}`).then(
                (result) => {
                    result.forEach((choiceEl) => {
                        choiceEl.value = choiceEl.id;
                        choiceEl.label = choiceEl.name;
                    });
                    resolve(result);
                }
            );
        });
        this.state.choices = choices;
    }
}
