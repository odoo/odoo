import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { TagsList } from "@web/core/tags_list/tags_list";
import { isId } from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { RecordAutocomplete } from "./record_autocomplete";
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
        useTagNavigation("multiRecordSelector", {
            delete: (index) => this.deleteTag(index),
        });
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    get isAvatarModel() {
        // bof
        return ["res.partner", "res.users", "hr.employee", "hr.employee.public"].includes(
            this.props.resModel
        );
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
        return this.getTags(this.props, {}).length ? "" : this.props.placeholder;
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
                img:
                    this.isAvatarModel &&
                    isId(id) &&
                    imageUrl(this.props.resModel, id, "avatar_128"),
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
