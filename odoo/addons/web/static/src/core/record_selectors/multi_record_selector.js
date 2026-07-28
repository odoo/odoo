/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";
import { RecordAutocomplete } from "./record_autocomplete";
import { _t } from "@web/core/l10n/translation";
import { useTagNavigation } from "./tag_navigation_hook";

export class MultiRecordSelector extends Component {
    static props = {
        resIds: { type: Array, element: Number },
        resModel: String,
        update: Function,
        domain: { type: Array, optional: true },
        context: { type: Object, optional: true },
        fieldString: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static components = { RecordAutocomplete, TagsList };
    static template = "web.MultiRecordSelector";

    setup() {
        this.nameService = useService("name");
        this.onTagKeydown = useTagNavigation("multiRecordSelector", this.deleteTag.bind(this));
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    async computeDerivedParams(props = this.props) {
        const displayNames = await this.getDisplayNames(props);
        this.tags = this.getTags(props, displayNames);
    }

    async getDisplayNames(props) {
        const ids = this.getIds(props);
        return this.nameService.loadDisplayNames(props.resModel, ids);
    }

    /**
     * Placeholder should be empty if there is at least one tag. We cannot use
     * the default behavior of the input placeholder because even if there is
     * a tag, the input is still empty.
     */
    get placeholder() {
        return this.getIds().length ? "" : this.props.placeholder;
    }

    getIds(props = this.props) {
        return props.resIds;
    }

    getTags(props, displayNames) {
        return props.resIds.map((id, index) => {
            const text =
                typeof displayNames[id] === "string"
                    ? displayNames[id]
                    : _t("Inaccessible/missing record ID: %s", id);
            return {
                text,
                onDelete: () => {
                    this.deleteTag(index);
                },
                onKeydown: this.onTagKeydown,
            };
        });
    }

    deleteTag(index) {
        this.props.update([
            ...this.props.resIds.slice(0, index),
            ...this.props.resIds.slice(index + 1),
        ]);
    }

    update(resIds) {
        this.props.update([...this.props.resIds, ...resIds]);
    }
}
