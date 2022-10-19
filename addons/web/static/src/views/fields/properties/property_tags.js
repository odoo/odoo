/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { ColorList } from "@web/core/colorlist/colorlist";
import { usePopover } from "@web/core/popover/popover_hook";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { sprintf } from "@web/core/utils/strings";

import { Component } from "@odoo/owl";

class PropertyTagsColorListPopover extends Component {}
PropertyTagsColorListPopover.template = "web.PropertyTagsColorListPopover";
PropertyTagsColorListPopover.components = {
    ColorList,
};

// property tags does not really need timeout because it does not make RPC calls
export class PropertyTagAutoComplete extends AutoComplete { };
Object.assign(PropertyTagAutoComplete, { timeout: 0 });

export class PropertyTags extends Component {
    setup() {
        this.notification = useService("notification");
        this.popover = usePopover();
    }

    /* --------------------------------------------------------
     * Public methods / Getters
     * -------------------------------------------------------- */

    /**
     * Return true if we should display the badges or just the tag label.
     *
     * @returns {array}
     */
    get displayBadge() {
        return !this.env.config || this.env.config.viewType !== "kanban";
    }

    /**
     * Return the list containing tags values and actions for the TagsList component.
     *
     * @returns {array}
     */
    get tagListItems() {
        if (!this.props.selectedTags || !this.props.selectedTags.length) {
            return [];
        }

        // Retrieve the tags label and color
        // ['a', 'b'] =>  [['a', 'A', 5], ['b', 'B', 6]]
        let value = this.props.tags.filter((tag) => this.props.selectedTags.indexOf(tag[0]) >= 0);

        if (!this.displayBadge) {
            // in kanban view e.g. to not show tag without color
            value = value.filter(tag => tag[2]);
        }

        const canDeleteTag = !this.props.readonly && this.props.canChangeTags;

        return value.map((tag) => {
            const [tagId, tagLabel, tagColorIndex] = tag;
            return {
                id: tagId,
                text: tagLabel,
                colorIndex: tagColorIndex || 0,
                onClick: (event) => this.onTagClick(event, tagId, tagColorIndex),
                onDelete: canDeleteTag && (() => this.onTagDelete(tagId)),
            };
        });
    }

    /**
     * Return the current selected tags.
     * Make a deep copy to not make change on the original object
     * and to be able to discard change.
     *
     * @returns {array}
     */
    get selectedTags() {
        return JSON.parse(JSON.stringify(this.props.selectedTags || []));
    }

    /**
     * Return the current tags that can be selected.
     * Make a deep copy to not make change on the original object
     * and to be able to discard change.
     *
     * @returns {array}
     */
    get availableTags() {
        return JSON.parse(JSON.stringify(this.props.tags || []));
    }

    /**
     * Options available in the autocomplete component.
     *
     * @returns {array}
     */
    get autocompleteSources() {
        return [
            {
                options: (request) => {
                    const tagsFiltered = this.props.tags.filter(
                        (tag) =>
                            (!this.props.selectedTags ||
                                this.props.selectedTags.indexOf(tag[0]) < 0) &&
                            (!request ||
                                !request.length ||
                                tag[1].toLocaleLowerCase().indexOf(request.toLocaleLowerCase()) >=
                                    0)
                    );
                    if (!tagsFiltered || !tagsFiltered.length) {
                        // no result, ask the user if he want to create a new tag
                        if (!request || !request.length) {
                            return [
                                {
                                    value: null,
                                    label: _lt("Start typing..."),
                                    classList: "fst-italic",
                                },
                            ];
                        } else if (!this.props.canChangeTags) {
                            return [
                                {
                                    value: null,
                                    label: _lt("No result"),
                                    classList: "fst-italic",
                                },
                            ];
                        }

                        return [
                            {
                                value: { toCreate: true, value: request },
                                label: sprintf(_lt('Create "%s"'), request),
                                classList: "o_field_property_dropdown_add",
                            },
                        ];
                    }
                    return tagsFiltered.map((tag) => {
                        return {
                            value: tag[0],
                            label: tag[1],
                        };
                    });
                },
            },
        ];
    }

    /* --------------------------------------------------------
     * Event handlers
     * -------------------------------------------------------- */

    /**
     * Add one value in the current tag list values.
     *
     * @param {string | object} tagValue
     *      Either
     *      - {toCreate: true, value: label}, to create a new value
     *      - value, to select an existing value
     */
    onOptionSelected(tagValue) {
        if (!tagValue) {
            // clicked on "Start typing..."
            return;
        }

        if (tagValue.toCreate) {
            this.onTagCreate(tagValue.value);
        } else {
            const selectedTags = this.selectedTags;
            const newValue = [...selectedTags, tagValue];
            this.props.onValueChange(newValue);
        }
    }

    /**
     * Ask to create a new tag that will be added in
     * the definition and automatically selected.
     *
     * @param {string} newLabel
     */
    onTagCreate(newLabel) {
        if (!newLabel || !newLabel.length) {
            return;
        }

        const newValue = newLabel ? newLabel.toLowerCase().replace(" ", "_") : "";

        const existingTag = this.props.tags.find((tag) => tag[0] === newValue);
        if (existingTag) {
            this.notification.add(_lt("This tag is already available"), {
                type: "warning",
            });
            return;
        }

        // cycle trough colors
        const tagColor =
            this.props.tags && this.props.tags.length
                ? (this.props.tags[this.props.tags.length - 1][2] + 1) % ColorList.COLORS.length
                : parseInt(Math.random() * ColorList.COLORS.length);

        const newTag = [newValue, newLabel, tagColor];
        const updatedTags = [...this.availableTags, newTag];
        // automatically select the newly created tag
        const newValues = [...this.props.selectedTags, newTag[0]];
        this.props.onTagsChange(updatedTags, newValues);
    }

    /**
     * Click on the delete button on the tag pill.
     * The behavior is defined by the prop "deleteAction".
     *
     * If we use the component for the tag configuration, clicking on "delete"
     * will remove the tags from the available tags. If we use the component
     * the the tag selection, it will unselect the tag.
     *
     * @param {string} deleteTag, ID of the tag to delete
     */
    onTagDelete(deleteTag) {
        if (this.props.deleteAction === "value") {
            // remove the tag from the value (but keep it in the options list)
            const selectedTags = this.selectedTags;
            const newValue = selectedTags.filter((tag) => tag !== deleteTag);
            this.props.onValueChange(newValue);
        } else {
            // remove the tag from the options
            const availableTags = this.availableTags;
            this.props.onTagsChange(availableTags.filter((tag) => tag[0] !== deleteTag));
        }
    }

    /**
     * Click on a tag pill, open the color popover if we can change the tag definition.
     *
     * @param {event} event
     * @param {string} tagId
     * @param {integer} tagColor
     */
    onTagClick(event, tagId, tagColor) {
        if (!this.props.canChangeTags) {
            event.currentTarget.blur();
            return;
        }
        this.popoverCloseFn = this.popover.add(
            event.currentTarget,
            this.constructor.components.Popover,
            {
                colors: [...Array(ColorList.COLORS.length).keys()],
                tag: { id: tagId, colorIndex: tagColor },
                switchTagColor: this.onTagColorSwitch.bind(this),
            },
            {
                closeOnClickAway: true,
            }
        );
    }

    /**
     * Ask to change the color of a tag.
     *
     * @param {integer} colorIndex
     * @param {object} currentTag
     */
    onTagColorSwitch(colorIndex, currentTag) {
        const availableTags = this.availableTags;
        availableTags.find((tag) => tag[0] === currentTag.id)[2] = colorIndex;
        this.props.onTagsChange(availableTags);

        // close the color popover
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }
}

PropertyTags.template = "web.PropertyTags";
PropertyTags.components = {
    AutoComplete: PropertyTagAutoComplete,
    TagsList,
    ColorList,
    Popover: PropertyTagsColorListPopover,
};

PropertyTags.props = {
    selectedTags: {}, // Tags value visible in the tags list
    tags: {}, // Tags definition visible in the dropdown
    // Define the behavior of the delete button on the tags, either
    // "value" or "tags". If "value", the delete button will unselect
    // the value, if "tags" the value will be removed from the definition.
    deleteAction: { type: String },
    readonly: { type: Boolean, optional: true },
    canChangeTags: { type: Boolean, optional: true },
    // Select a new value
    onValueChange: { type: Function, optional: true },
    // Change the tags definition (can also receive a second
    // argument to update the current selected value)
    onTagsChange: { type: Function, optional: true },
};
