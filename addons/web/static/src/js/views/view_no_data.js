odoo.define('web.viewNoData', function (require) {
    "use strict";

    var viewNoData = {
        isSample: true,
        _makeSampleData: function(model, listFields) {
            this.session = model.getSession();
            var sampleData = {
                length: 0,
                records: [],
                isSample: true,
            };
            for(this.i = 0; this.i < 4; this.i++) {
                sampleData.records.push(this._buildSampleData(listFields));
            }
            return sampleData;
        },
        _buildSampleData: function (listFields) {
            var self = this;
            let data = {};
            let date = new moment().add({
                'minutes': Math.floor((Math.random() - Math.random()) * 31 * 24 * 7 * 60),
            }).format("YYYY-MM-DD HH:mm:ss");
            let sampleUser = ["John Miller", "Henry Campbell", "Carrie Helle", "Wendi Baltz", "Thomas Passot"];
            let sampleText = ["Laoreet id", "Volutpat blandit", "Integer vitae", "Viverra nam", "In massa"];
            Object.keys(listFields).forEach(function (field) {
                if (!field.includes("activity_exception")) {
                    let f = listFields[field];
                    if (f.type === "char" || f.type === "text") {
                        if (field === "json_activity_data") {
                            data[field] = '{"activities": {}}';
                        } else if (field.includes("dashboard")) {
                            data[field] = false;
                        } else if (field === "name") {
                            data[field] = `REF000${self.i}`;
                        } else if (field.includes("email")) {
                            data[field] = `sample${self.i}@sample.demo`;
                        } else if (field.includes("phone")) {
                            data[field] = `+1 555 754 000${self.i}`;
                        } else {
                            data[field] = sampleText[Math.floor(Math.random() * 5)];
                        }
                    } else if (f.type === "selection") {
                        if ((Math.random() > 0.4 || f.store) && f.selection.length > 0) {
                            data[field] = f.selection[Math.floor(Math.random() * f.selection.length)][0];
                        }
                    } else if (f.type === "monetary") {
                        data[field] = Math.floor(Math.random() * 100000);
                    } else if (f.type === "many2one") {
                        if (field === "user_id" || field === "partner_id" || field === "employee_id") {
                            data[field] = [1, sampleUser[Math.floor(Math.random() * 5)]];
                        } else if (f.relation === 'res.currency') {
                            data[field] = [self.session.company_currency_id];
                        } else {
                            data[field] = [1, sampleText[Math.floor(Math.random() * 5)]];
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
        _makeSampleRow: function(groupedBy, records) {
            return [{
                name: `REF0000`,
                groupId: `group0`,
                groupedBy: groupedBy,
                groupedByField: groupedBy[0],
                id: `row0`,
                isGroup: false,
                isOpen: true,
                path: `[0,"test 0"]`,
                records: records,
            }];
        },
    };
    return viewNoData;
});