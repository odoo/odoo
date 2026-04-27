import { SearchModel } from "@web/search/search_model";

export class ProjectTaskSearchModel extends SearchModel {
    exportState() {
        return {
            ...super.exportState(),
            highlightPlannedIds: this.highlightPlannedIds,
        };
    }

    _importState(state) {
        this.highlightPlannedIds = state.highlightPlannedIds;
        super._importState(state);
    }

    deactivateGroup(groupId) {
        if (this._getHighlightPlannedSearchItems()?.groupId === groupId) {
            this.highlightPlannedIds = null;
        }
        super.deactivateGroup(groupId);
    }

    toggleHighlightPlannedFilter(highlightPlannedIds) {
        const highlightPlannedSearchItems = this._getHighlightPlannedSearchItems();
        if (highlightPlannedIds) {
            this.highlightPlannedIds = highlightPlannedIds;
            if (highlightPlannedSearchItems) {
                if (
                    this.query.find(
                        (queryElem) => queryElem.searchItemId === highlightPlannedSearchItems.id
                    )
                ) {
                    this._notify();
                } else {
                    this.toggleSearchItem(highlightPlannedSearchItems.id);
                }
            }
        } else if (highlightPlannedSearchItems) {
            this.deactivateGroup(highlightPlannedSearchItems.groupId);
        }
    }

    _getHighlightPlannedSearchItems() {
        return Object.values(this.searchItems).find((v) => v.name === "tasks_scheduled");
    }
}
