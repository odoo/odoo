import { Component } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';

export const COLLAPSE_ICONS = {
    collapse_composition: 'close_fullscreen',
    collapse_prices: 'visibility_off',
}

export class SectionStateIcon extends Component {
    static template = 'account.SectionStateIcon';
    static props = {
        ...standardWidgetProps,
        iconMapping: Object,
    };

    get icon() {
        for (const [field, icon] of Object.entries(this.props.iconMapping)) {
            if (this.props.record.data[field]) {
                return icon;
            }
        }

        return '';
    }
}

export const sectionStateIcon = {
    component: SectionStateIcon,
    extractProps: ({ options }) => ({
        iconMapping: {
            ...COLLAPSE_ICONS,
            ...options,
        },
    }),
    listViewWidth: 20,
};

registry.category('view_widgets').add('section_state', sectionStateIcon);
