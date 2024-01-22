/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {rankInterval} from "@web/search/utils/dates";
import {SearchModel} from "@web/search/search_model";

patch(SearchModel.prototype, "web_search_with_and/static/src/js/search_model.js", {
    _getGroups() {
        const preGroups = [];
        for (const queryElem of this.query) {
            const {searchItemId} = queryElem;
            let {groupId} = this.searchItems[searchItemId];
            if ("autocompleteValue" in queryElem) {
                if (queryElem.autocompleteValue.isShiftKey) {
                    groupId = Math.random();
                }
            }
            let preGroup = preGroups.find((group) => group.id === groupId);
            if (!preGroup) {
                preGroup = {id: groupId, queryElements: []};
                preGroups.push(preGroup);
            }
            queryElem.groupId = groupId;
            preGroup.queryElements.push(queryElem);
        }
        const groups = [];
        for (const preGroup of preGroups) {
            const {queryElements, id} = preGroup;
            const activeItems = [];
            for (const queryElem of queryElements) {
                const {searchItemId} = queryElem;
                let activeItem = activeItems.find(
                    ({searchItemId: id}) => id === searchItemId
                );
                if ("generatorId" in queryElem) {
                    if (!activeItem) {
                        activeItem = {searchItemId, generatorIds: []};
                        activeItems.push(activeItem);
                    }
                    activeItem.generatorIds.push(queryElem.generatorId);
                } else if ("intervalId" in queryElem) {
                    if (!activeItem) {
                        activeItem = {searchItemId, intervalIds: []};
                        activeItems.push(activeItem);
                    }
                    activeItem.intervalIds.push(queryElem.intervalId);
                } else if ("autocompleteValue" in queryElem) {
                    if (!activeItem) {
                        activeItem = {searchItemId, autocompletValues: []};
                        activeItems.push(activeItem);
                    }
                    activeItem.autocompletValues.push(queryElem.autocompleteValue);
                } else if (!activeItem) {
                    activeItem = {searchItemId};
                    activeItems.push(activeItem);
                }
            }
            for (const activeItem of activeItems) {
                if ("intervalIds" in activeItem) {
                    activeItem.intervalIds.sort(
                        (g1, g2) => rankInterval(g1) - rankInterval(g2)
                    );
                }
            }
            groups.push({id, activeItems});
        }

        return groups;
    },
    deactivateGroup(groupId) {
        this.query = this.query.filter((queryElem) => {
            return queryElem.groupId !== groupId;
        });

        for (const partName in this.domainParts) {
            const part = this.domainParts[partName];
            if (part.groupId === groupId) {
                this.setDomainParts({[partName]: null});
            }
        }
        this._checkComparisonStatus();
        this._notify();
    },
});
