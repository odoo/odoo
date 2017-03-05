odoo.define('web.KanbanModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');

return BasicModel.extend({
    load: function (params) {
        this.defaultGroupedBy = params.groupBy;
        params.groupedBy = params.groupedBy.length ? params.groupedBy : this.defaultGroupedBy;
        return this._super(params);
    },
    reload: function (id, options) {
        // if the groupBy is given in the options and if it is an empty array,
        // fallback on the default groupBy
        if (options && options.groupBy && !options.groupBy.length) {
            options.groupBy = this.defaultGroupedBy;
        }
        return this._super(id, options);
    },
    addRecordToGroup: function (group_id, res_id) {
        var group = this.localData[group_id];
        var new_record = this._makeDataPoint({
            res_id: res_id,
            modelName: group.model,
            fields: group.fields,
            fieldNames: group.fieldNames,
            fieldAttrs: group.fieldAttrs,
        });
        group.data.unshift(new_record);
        group.count++;
        return this._fetchRecord(new_record)
            // .then(this._fetch_relational_data.bind(this))
            .then(function (result) {
                return result.id;
            });
    },
    moveRecord: function (record_id, group_id, parent_id) {
        var self = this;
        var parent = this.localData[parent_id];
        var new_group = this.localData[group_id];
        var changes = {};
        var groupedFieldName = parent.groupedBy[0];
        var groupedField = parent.fields[groupedFieldName];
        if (groupedField.type === 'many2one') {
            changes[groupedFieldName] = {
                id: new_group.res_id,
                display_name: new_group.value,
            };
        } else {
            changes[groupedFieldName] = new_group.value;
        }
        return this.notifyChanges(record_id, changes).then(function () {
            return self.save(record_id);
        }).then(function (result) {
            // Remove record from its current group
            var old_group;
            for (var i = 0; i < parent.count; i++) {
                old_group = self.localData[parent.data[i]];
                var index = _.indexOf(old_group.data, record_id);
                if (index >= 0) {
                    old_group.data.splice(index, 1);
                    old_group.count--;
                    break;
                }
            }
            // Add record to its new group
            new_group.data.push(result.id);
            new_group.count++;
            return [old_group.id, new_group.id];
        });
    },
    resequence: function (modelName, res_ids, parent_id) {
        if ((res_ids.length <= 1)) {
            return $.when(parent_id); // there is nothing to sort
        }
        var self = this;
        var data = self.localData[parent_id];
        var def;
        if (data.fields.sequence) {
            def = this.performRPC('/web/dataset/resequence', {
                model: modelName,
                ids: res_ids,
                // fixme: correctly handle context
            });
        }
        return $.when(def).then(function () {
            data.data = _.sortBy(data.data, function (d) {
                return _.indexOf(res_ids, d.res_id);
            });
            return parent_id;
        });
    },
    createGroup: function (name, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        var groupBy = parent.groupedBy[0];
        var groupByField = parent.fields[groupBy];
        if (!groupByField || groupByField.type !== 'many2one') {
            return $.Deferred().reject(); // only supported when grouped on m2o
        }
        return this.rpc(groupByField.relation, 'name_create')
            .args([name])
            .withContext(parent.context) // todo: combine with view context
            .exec()
            .then(function (result) {
                var newGroup = self._makeDataPoint({
                    modelName: parent.model,
                    context: parent.context,
                    domain: parent.domain.concat([[groupBy,"=",result[0]]]),
                    fields: parent.fields,
                    fieldNames: parent.fieldNames,
                    groupedBy: parent.groupedBy,
                    isOpen: true,
                    limit: parent.limit,
                    openGroupByDefault: true,
                    orderedBy: parent.orderedBy,
                    value: result,
                });

                // newGroup.is_open = true;
                parent.data.push(newGroup.id);
                parent.count++;
                return newGroup.id;
            });
    },
});

});
