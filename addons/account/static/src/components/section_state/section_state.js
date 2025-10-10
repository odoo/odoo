import { Component } from '@odoo/owl';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { registry } from '@web/core/registry';

export class SectionState extends Component {
    static template = 'account.SectionState';
    static props = {
        ...standardWidgetProps,
    };

    get iconInfo(){
        if (this.props.record.data.collapse_composition) {
            return {
                iconClass: 'fa fa-compress text-muted',
                title: this.props.record.fields.collapse_composition.help,
            };
        } else if (this.props.record.data.collapse_prices) {
            return {
                iconClass: 'fa fa-eye-slash text-muted',
                title: this.props.record.fields.collapse_prices.help,
            };
        }
        return {};
    }
}

export const sectionStateWidget = {
    component: SectionState,
    listViewWidth: 20,
};

registry.category('view_widgets').add('section_state', sectionStateWidget);
