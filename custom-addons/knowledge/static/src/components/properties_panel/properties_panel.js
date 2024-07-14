/** @odoo-module **/

import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';

import { PropertiesField } from '@web/views/fields/properties/properties_field';

import { Component, useRef, useState } from '@odoo/owl';

export class KnowledgeArticleProperties extends Component {
    static template = 'knowledge.KnowledgeArticleProperties';
    static props = { ...standardWidgetProps };
    static components = { PropertiesField };

    setup() {
        this.state = useState({
            displayPropertyPanel: false,
        });

        this.root = useRef('root');

        this.env.bus.addEventListener('KNOWLEDGE:TOGGLE_PROPERTIES', this.toggleProperties.bind(this));
    }

    get showNoContentHelper() {
        return this.props.record.data.article_properties.every((prop) => prop.definition_deleted);
    }

    toggleProperties(event) {
        this.state.displayPropertyPanel = event.detail.displayPropertyPanel;
        if (this.state.displayPropertyPanel) {
            this.root.el?.parentElement?.classList.remove('d-none');
        } else {
            this.root.el?.parentElement?.classList.add('d-none');
        }
    }
}


export const knowledgePropertiesPanel = {
    component: KnowledgeArticleProperties,
    additionalClasses: [
        'o_knowledge_properties',
        'o_field_highlight',
        'col-12',
        'col-lg-2',
        'position-relative',
        'd-none',
        'p-0',
        'border-start'
    ]
};

registry.category('view_widgets').add('knowledge_properties_panel', knowledgePropertiesPanel);
