import { Component } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';

const cogMenuRegistry = registry.category('cogMenu');

export class ExpandAll extends Component {
	
    static template = 'muk_web_group.ExpandAll';
    static components = { DropdownItem };
    static props = {};

    async onExpandButtonClicked() {
        let groups = this.env.model.root.groups;
        while (groups.length) {
            const foldedGroups = groups.filter(
            	(group) => group._config.isFolded
            );
            if (foldedGroups.length) {
            	for (const group of foldedGroups) {
            		await group.toggle();
                }
            }
            const subGroups = foldedGroups.map(
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

export const expandAllItem = {
    Component: ExpandAll,
    groupNumber: 15,
    isDisplayed: async (env) => (
        ['kanban', 'list'].includes(env.config.viewType) && 
        env.model.root.isGrouped
    )
};

cogMenuRegistry.add('expand-all-menu', expandAllItem, { sequence: 1 });
