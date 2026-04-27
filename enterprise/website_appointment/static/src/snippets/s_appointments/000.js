import publicWidget from '@web/legacy/js/public/public_widget';
import DynamicSnippet from '@website/snippets/s_dynamic_snippet/000';
import { Domain } from "@web/core/domain";


const AppointmentsListSnippet = DynamicSnippet.extend({
    selector: '.s_appointments',
    disabledInEditableMode: false,
    /**
     * @override
     * @private
     */
    _getSearchDomain: function () {
        let searchDomain = new Domain(this._super(...arguments));
        const snippetDataset = this.el.dataset;
        const filterType = snippetDataset.filterType;
        const appointmentNames = (snippetDataset.appointmentNames || '')
            .split(',')
            .map((name) => name.trim())
            .filter((name) => name.length > 0);

        if (filterType === 'users') {
            searchDomain = Domain.and([searchDomain, [['schedule_based_on', '=', 'users']]]);
            if (snippetDataset.filterUsers) {
                const filterUserIds = JSON.parse(snippetDataset.filterUsers).map(u => u.id);
                if (filterUserIds.length !== 0) {
                    searchDomain = Domain.and([searchDomain, [['staff_user_ids', 'in', filterUserIds]]]);
                }
            }
        } else if (filterType === 'resources') {
            searchDomain = Domain.and([searchDomain, [['schedule_based_on', '=', 'resources']]]);
            if (snippetDataset.filterResources) {
                const filterResourceIds = JSON.parse(snippetDataset.filterResources).map(r => r.id);
                if (filterResourceIds.length !== 0) {
                    searchDomain = Domain.and([searchDomain, [['resource_ids', 'in', filterResourceIds]]]);
                }
            }
        }
        if (appointmentNames.length > 0) {
            const nameDomains = appointmentNames.map((name) => [['name', 'ilike', name]]);
            searchDomain = Domain.and([searchDomain, Domain.or(nameDomains)]);
        }
        return searchDomain.toList();
    },
    /**
     * @override
     * @private
     */
    _getMainPageUrl() {
        return "/appointment";
    },
});

publicWidget.registry.s_appointments = AppointmentsListSnippet;

export default AppointmentsListSnippet;
