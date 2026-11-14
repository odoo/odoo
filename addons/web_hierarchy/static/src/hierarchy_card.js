import { useProps, t, computed } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { CardRenderer, cardRendererProps } from "@web/views/card/card_renderer";

export class HierarchyCard extends CardRenderer {
    static template = "web_hierarchy.HierarchyCard";

    props = useProps({
        ...cardRendererProps,
        openRecord: t.function(),
        classNames: t.string().optional(""),
        isParentNode: t.boolean().optional(false),
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

    get renderingContext() {
        return { ...super.renderingContext, parentId: this.parent().id };
    }

    showAncestorLabel() {
        return _t("Show %s", this.parent().fieldName.toLowerCase());
    }

    unfoldLabel() {
        const { count, fieldName } = this.children();
        return _t("%(count)s %(label)s", { count, label: fieldName || _t('Unfold') });
    }

    getCardClasses() {
        return ['bg-view', super.getCardClasses(), this.props.classNames].join(' ');
    }

    onGlobalClick(ev, newWindow) {
        if (ev.target.closest("button")) {
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

    _openHierarchyOf(resId, name) {
        const { resModel, model: { parentFieldName }, context } = this.props.record;
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                name,
                res_model: resModel,
                views: this.env.config.views,
                domain: [[parentFieldName, "=", resId]],
                context,
                target: "current",
            },
            { viewType: "hierarchy" },
        );
    }
}
