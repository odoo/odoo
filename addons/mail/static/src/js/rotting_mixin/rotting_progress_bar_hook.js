export const rottingProgressBarPatch = {
    rotIsFiltered: {},
    async toggleFilterRotten(group) {
        if (!this.rotIsFiltered[group.id]) {
            await this.setFilterRotten(group);
        } else {
            await this.unsetFilterRotten(group);
        }
        group.model.notify();
    },
    async setFilterRotten(group) {
        await group.applyFilter([["is_rotting", "=", true]]);
        this.rotIsFiltered[group.id] = group;
        if (this.activeBars[group.serverValue]) {
            delete this.activeBars[group.serverValue];
        }
    },
    async unsetFilterRotten(group) {
        await group.applyFilter(undefined);
        delete this.rotIsFiltered[group.id];
    },
    /**
     * @override
     */
    async selectBar(groupId, bar) {
        if (this.rotIsFiltered[groupId]) {
            delete this.rotIsFiltered[groupId];
        }
        return super.selectBar(groupId, bar);
    },
    /**
     * @override
     */
    getGroupCount(group) {
        if (this.rotIsFiltered[group.id]) {
            return group.list.records.filter((record) => record.data.is_rotting).length;
        }
        return super.getGroupCount(group);
    },
};
