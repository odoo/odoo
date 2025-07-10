export const rottingProgressBarPatch = {
    rotIsFiltered: {},
    async toggleFilterRotten(groupId) {
        const group = this.model.root.groups.find((group) => group.id === groupId);
        if (!this.rotIsFiltered[groupId]) {
            await this.setFilterRotten(group);
            this.rotIsFiltered[groupId] = group;
        } else {
            await this.unsetFilterRotten(group);
            delete this.rotIsFiltered[groupId];
            //if (activeGroupBar) {
            //    await this.selectBar(groupId, activeGroupBar.value);
            //}
        }
    },
    /**
     * @override
     */
    async selectBar(groupId, bar) {
        //const ret = super.selectBar(groupId, bar);
        if (this.rotIsFiltered[groupId]) {
            this.unsetFilterRotten(this.rotIsFiltered[groupId]);
            delete this.rotIsFiltered[groupId];
        }
        return super.selectBar(groupId, bar);
        //if (this.rotIsFiltered[groupId]) {
        //    await this.setFilterRotten(this.rotIsFiltered[groupId]);
        //}
        //return ret;
    },
    async setFilterRotten(group) {
        await group.applyFilter([[this.progressAttributes.rotting_count_field.name, "=", true]]);
        //this.updateCounts(group);
    },
    async unsetFilterRotten(group) {
        await group.applyFilter(undefined);
        group.model.notify();
    },
};
