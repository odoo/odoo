import { useProps, t } from "@odoo/owl";

import { CardRenderer, cardRendererProps } from "@web/views/card/card_renderer";

export class HierarchyCard extends CardRenderer {
    static template = "web_hierarchy.HierarchyCard";

    props = useProps({
        ...cardRendererProps,
        openRecord: t.function(),
        classNames: t.string().optional(""),
        model: t.object(),
        leaf: t.boolean(),
    });

    get countChildren() {
        return this.props.record.data[this.props.model.childFieldName]?.count;
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

    toggleChildren() {
        if (this.props.leaf) {
            this.props.model.load({ targetParentResId: this.props.record.resId });
        } else {
            const parent = this.props.record.data[this.props.model.parentFieldName];
            this.props.model.load({ targetParentResId: parent.id || false });
        }
    }
}
