odoo.define('web.viewNoData', function (require) {
    "use strict";

    var Class = require('web.Class');

    var FakeServer = Class.extend({
        init: function (params) {
            this.params = params;
            this.route = params.route;
            this.method = params.method;
            this.listFields = params.fields,
            this.session = params.session;
        },
        isEmpty: function (result) {
            var self = this;
            if (_.isEmpty(result) || result.length === 0) {
                return true;
            } else {
                switch (this.method) {
                    case 'web_read_group':
                        let total = 0;
                        _.each(result.groups, function (group) {
                            let counter = self.params.defaultGroupedBy || Object.keys(group).find(key => key.includes('_count'));
                            total += group[counter];
                        });
                        return !total;
                }
            }
            return false;
        },
        performRpc: function (result) {
            return Promise.resolve(this._performRpc(result));
        },
        _performRpc: function (result) {
            var self = this;
            switch (this.route) {
                case '/web/dataset/search_read':
                    return this._fakeSearchRead();
            }
            switch (this.method) {
                case 'web_read_group':
                    if (JSON.stringify(this.params.initialDomain) === JSON.stringify(this.params.domain)) {
                        _.each(result.groups, function (group) {
                            let counter = self.params.defaultGroupedBy || Object.keys(group).find(key => key.includes('_count'));
                            group[counter] = 4;
                        });
                    }
                    return result;
            }
            return result || {};
        },
        _fakeSearchRead: function () {
            const listFields = this.listFields;
            var result = {
                length: 0,
                records: [],
            };
            for (; result.length < 4; result.length++) {
                result.records.push(this._buildSampleRecords(listFields));
            }
            return result;
        },
        _buildSampleRecords: function (listFields) {
            var self = this;
            let data = {};
            let date = new moment().add({
                'minutes': Math.floor((Math.random() - Math.random()) * 31 * 24 * 7 * 60),
            }).format("YYYY-MM-DD HH:mm:ss");
            let sampleUser = ["John Miller", "Henry Campbell", "Carrie Helle", "Wendi Baltz", "Thomas Passot"];
            let sampleText = ["Laoreet id", "Volutpat blandit", "Integer vitae", "Viverra nam", "In massa"];
            let randomID = Math.floor(Math.random() * 5);
            Object.keys(listFields).forEach(function (field) {
                if (!field.includes("activity_exception")) {
                    let f = listFields[field];
                    if (f.type === "char" || f.type === "text") {
                        if (field === "json_activity_data") {
                            data[field] = '{"activities": {}}';
                        } else if (field.includes("dashboard")) {
                            data[field] = false;
                        } else if (field === "name") {
                            data[field] = `REF000${randomID}`;
                        } else if (field.includes("email")) {
                            data[field] = `sample${randomID}@sample.demo`;
                        } else if (field.includes("phone")) {
                            data[field] = `+1 555 754 000${randomID}`;
                        } else {
                            data[field] = sampleText[randomID];
                        }
                    } else if (f.type === "selection") {
                        if ((Math.random() > 0.4 || f.store) && f.selection.length > 0) {
                            data[field] = f.selection[Math.floor(Math.random() * f.selection.length)][0];
                        }
                    } else if (f.type === "monetary") {
                        data[field] = Math.floor(Math.random() * 100000);
                    } else if (f.type === "many2one") {
                        if (field === "user_id" || field === "partner_id" || field === "employee_id") {
                            data[field] = [1, sampleUser[randomID]];
                        } else if (f.relation === 'res.currency') {
                            data[field] = [self.session.company_currency_id];
                        } else {
                            data[field] = [1, sampleText[randomID]];
                        }
                    } else if (f.type === "one2many" || f.type === "many2many") {
                        data[field] = [];
                    } else if (f.type === "date" || f.type === "datetime") {
                        data[field] = date;
                    } else if (f.type === "boolean") {
                        data[field] = false;
                    } else if (f.type === "float") {
                        data[field] = Math.random() * 100;
                    } else if (f.type === "integer") {
                        if (field.includes('color')) {
                            if (Math.random() > 0.7) {
                                data[field] = Math.ceil(Math.random() * 42);
                            }
                        } else {
                            data[field] = Math.ceil(Math.random() * 42);
                        }
                    } else if (f.type === "binary") {
                        data[field] = 0;
                    }
                }
            });
            return data;
        },
    });

    return FakeServer;
});