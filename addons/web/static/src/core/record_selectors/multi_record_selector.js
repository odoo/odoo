import { Component, onWillStart, onWillUpdateProps, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { AvatarTag } from "@web/core/tags_list/avatar_tag";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { isId } from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { RecordAutocomplete } from "./record_autocomplete";
import { useTagNavigation } from "./tag_navigation_hook";

export const multiRecordSelectorProps = {
    // no element type: subclasses (e.g. DomainSelectorAutocomplete) accept
    // expressions too, and the base schema is still validated for them
    resIds: t.array(),
    resModel: t.string(),
    update: t.function(),
    domain: t.array().optional(),
    context: t.object().optional(),
    fieldString: t.string().optional(),
    placeholder: t.string().optional(),
};

export class MultiRecordSelector extends Component {
    props = useProps(multiRecordSelectorProps);
    static components = { AvatarTag, BadgeTag, RecordAutocomplete };
    static template = "web.MultiRecordSelector";

    multiRecordSelectorRef = signal(null);

    setup() {
        this.nameService = useService("name");
        useTagNavigation(this.multiRecordSelectorRef, {
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
        /**
         * Placeholder should be empty if there is at least one tag. We cannot use
         * the default behavior of the input placeholder because even if there is
         * a tag, the input is still empty.
         */
        this.placeholder = this.tags.length ? "" : this.props.placeholder;
    }

    async getDisplayNames(props) {
        const ids = this.getIds(props);
        return this.nameService.loadDisplayNames(props.resModel, ids);
    }

    getIds(props = this.props) {
        return props.resIds;
    }

    getTags(props, displayNames) {
        return props.resIds.map((id, index) => {
            const text = typeof displayNames[id] === "string" ? displayNames[id] : String(id);
            return {
                id,
                text,
                tooltip:
                    typeof displayNames[id] === "string" ? text : _t("Missing record (ID: %s)", id),
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
