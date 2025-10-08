import { SectionState, sectionStateWidget } from '@account/components/section_state/section_state';
import { registry } from '@web/core/registry';

export class SaleManagementSectionState extends SectionState {
    get iconInfo() {
        if (this.props.record.data.is_optional) {
            return {
                iconClass: 'fa fa-dot-circle-o text-muted',
                title: this.props.record.fields.is_optional.help,
            };
        }
        return super.iconInfo;
    }
}

export const saleManagementSectionStateWidget = {
    ...sectionStateWidget,
    component: SaleManagementSectionState,
};

registry
    .category('view_widgets')
    .add('sale_management_section_state', saleManagementSectionStateWidget);
