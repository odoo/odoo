import { Component } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';

const cogMenuRegistry = registry.category('cogMenu');

export class CollapseAll extends Component {

    static template = 'muk_web_group.CollapseAll';
    static components = { DropdownItem };
    static props = {};

    async onCollapseButtonClicked() {
        let groups = this.env.model.root.groups;
        while (groups.length) {
            const unfoldedGroups = groups.filter(
            	(group) => !group._config.isFolded
            );
            if (unfoldedGroups.length) {
            	for (const group of unfoldedGroups) {
            		await group.toggle();
                }
            }
            const subGroups = unfoldedGroups.map(
            	(group) => group.list.groups || []
            );
            groups = subGroups.reduce( 
            	(a, b) => a.concat(b), []
            );
        }
        await this.env.model.root.load();
        this.env.model.notify();
    }
}

export const collapseAllItem = {
    Component: CollapseAll,
    groupNumber: 15,
    isDisplayed: async (env) => (
        ['kanban', 'list'].includes(env.config.viewType) && 
        env.model.root.isGrouped
    )
};

cogMenuRegistry.add('collapse-all-menu', collapseAllItem, { sequence: 2 });
