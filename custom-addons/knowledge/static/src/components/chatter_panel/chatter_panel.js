/** @odoo-module **/

import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';

import { useService } from "@web/core/utils/hooks";
import { Chatter } from '@mail/core/web/chatter';
import { SIZES } from "@web/core/ui/ui_service";


import { Component, useRef, useState } from '@odoo/owl';

export class KnowledgeArticleChatter extends Component {
    static template = 'knowledge.KnowledgeArticleChatter';
    static components = { Chatter };
    static props = { ...standardWidgetProps };

    setup() {
        this.state = useState({
            displayChatter: false,
        });

        this.root = useRef('root')
        this.ui = useService("ui");

        this.env.bus.addEventListener('KNOWLEDGE:TOGGLE_CHATTER', this.toggleChatter.bind(this));
    }

    toggleChatter(event) {
        this.state.displayChatter = event.detail.displayChatter;
        if (this.state.displayChatter) {
            this.root.el?.parentElement?.classList.remove('d-none');
        } else {
            this.root.el?.parentElement?.classList.add('d-none');
        }
    }

    get isChatterAside() {
        return this.ui.size >= SIZES.LG;
    }
}

export const knowledgeChatterPanel = {
    component: KnowledgeArticleChatter,
    additionalClasses: [
        'o_knowledge_chatter',
        'col-12',
        'col-lg-4',
        'position-relative',
        'd-none',
        'p-0',
        'test'
    ]
};

registry.category('view_widgets').add('knowledge_chatter_panel', knowledgeChatterPanel);
