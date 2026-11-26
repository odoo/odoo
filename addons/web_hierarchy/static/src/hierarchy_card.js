import { useProps, t, computed } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { CardRenderer, cardRendererProps } from "@web/views/card/card_renderer";

export class HierarchyCard extends CardRenderer {
    static template = "web_hierarchy.HierarchyCard";

    props = useProps({
        ...cardRendererProps,
        openRecord: t.function(),
        showAncestorBtn: t.boolean().optional(true),
        showChildrenBtn: t.boolean().optional(true),
    });

    children = computed(() => {
        const { model: { childFieldName }, data, fields } = this.props.record;
        return {
            count: data[childFieldName]?.count || 0,
            fieldName: fields[childFieldName].string,
        };
    });

    parent = computed(() => {
        const { model: { parentFieldName }, data, fields } = this.props.record;
        return {
            id: data[parentFieldName]?.id || false,
            displayName: data[parentFieldName]?.display_name || "",
            fieldName: fields[parentFieldName].string,
        };
    });

    showChildrenBtn = computed(() => {
        return this.props.showChildrenBtn && this.children().count;
    });

    get renderingContext() {
        return { ...super.renderingContext, parentId: this.parent().id };
    }

    showAncestorLabel() {
        return _t("Show %s", this.parent().fieldName.toLowerCase());
    }

    unfoldLabel() {
        const { count, fieldName } = this.children();
        return `${count} ${fieldName}`;
    }

    getCardClasses() {
        return ['bg-view', super.getCardClasses()].join(' ');
    }

    onGlobalClick(ev, newWindow) {
        if (ev.target.closest("button") || ev.target.closest("a")) {
            return;
        }
        this.props.openRecord(this.props.record, newWindow);
    }

    unfold() {
        const { resId, data: { display_name: displayName } } = this.props.record;
        return this._openHierarchyOf(resId, displayName);
    }

    showAncestor() {
        const { id, displayName } = this.parent();
        return this._openHierarchyOf(id, displayName);
    }

    /**
     * Opens the hierarchy view on the record `resId` and its children.
     */
    _openHierarchyOf(resId, name) {
        const { resModel, model: { parentFieldName }, context } = this.props.record;
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                name,
                res_model: resModel,
                views: this.env.config.views,
                domain: ["|", ["id", "=", resId], [parentFieldName, "=", resId]],
                context,
                target: "current",
            },
            { viewType: "hierarchy" },
        );
    }
}
