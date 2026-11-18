import { useProps, t } from "@odoo/owl";

import { CardRenderer, cardRendererProps } from "@web/views/card/card_renderer";

export class HierarchyCard extends CardRenderer {
    static template = "web_hierarchy.HierarchyCard";

    props = useProps({
        ...cardRendererProps,
        openRecord: t.function(),
        classNames: t.string().optional(""),
    });

    get renderingContext() {
        return {
            ...super.renderingContext,
            parentResId: this.props.record.parentResId,
        };
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
}
