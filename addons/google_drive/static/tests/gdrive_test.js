odoo.define('google_drive.gdrive_integration', function (require) {
"use strict";
//rebuild
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var GoogleDriveSideBar = require('google_drive.sidebar');

var createView = testUtils.createView;

/*
 * @override
 * Avoid breaking other tests because of the new route
 * that the module introduces
 */
var _addGoogleDocItemsOriginal = GoogleDriveSideBar.prototype._addGoogleDocItems;

var _addGoogleDocItemsMocked = function (model, resID) {
    return $.when();
};

GoogleDriveSideBar.prototype._addGoogleDocItems = _addGoogleDocItemsMocked;

QUnit.module('gdrive_integration', {
    beforeEach: function () {
        // For our test to work, the _addGoogleDocItems function needs to be the original
        GoogleDriveSideBar.prototype._addGoogleDocItems = _addGoogleDocItemsOriginal;

        this.data = {
            partner: {
                fields: {
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                },
                records: [{
                    id: 1,
                    display_name: "Locomotive Breath",
                }, {
                    id: 2,
                    display_name: "Hey Macarena",
                }],
            },
            'google.drive.config': {
                fields: {
                    model_id: {string: 'Model', type: 'int'},
                    name: {string: 'Name', type: 'char'},
                    google_drive_resource_id: {string: 'Resource ID', type: 'char'},
                },
                records: [{
                    id: 27,
                    name: 'Cyberdyne Systems',
                    model_id: 1,
                    google_drive_resource_id: 'T1000',
                }],
            },
            'ir.attachment': {
                fields: {
                    name: {string: 'Name', type:'char'}
                },
                records: [],
            }
        };
    },

    afterEach: function() {
        GoogleDriveSideBar.prototype._addGoogleDocItems = _addGoogleDocItemsMocked;
    }

}, function () {
    QUnit.module('Google Drive Sidebar');

    QUnit.test('rendering of the google drive attachments in Sidebar', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="display_name"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {sidebar: true},
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/google.drive.config/get_google_drive_config') {
                    assert.deepEqual(args.args, ['partner', 1],
                        'The route to get google drive config should have been called');
                    return $.when([{id: 27, name: 'Cyberdyne Systems'}]);
                }
                if (route === '/web/dataset/call_kw/google.drive.config/search_read'){
                    return $.when([{google_drive_resource_id: "T1000",
                                    google_drive_client_id: "cyberdyne.org",
                                    id: 1}]);
                }
                if (route === '/web/dataset/call_kw/google.drive.config/get_google_drive_url') {
                    assert.deepEqual(args.args, [27, 1, 'T1000'],
                        'The route to get the Google url should have been called');
                    // We don't return anything useful, otherwise it will open a new tab
                    return $.when();
                }
                return this._super.apply(this, arguments);
            }
        });

        var google_action = form.sidebar.$('.oe_share_gdoc');

        assert.strictEqual(google_action.length, 1,
            'The button to the google action should be present');

        // Trigger opening of the dynamic link
        google_action.find('a:first').click();
        form.destroy();
    });

    QUnit.test('click on the google drive attachments after switching records', function (assert) {
        assert.expect(3);
        var self = this;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="display_name"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                sidebar: true,
                ids: [1, 2],
                index: 0,
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/google.drive.config/get_google_drive_config') {
                    assert.deepEqual(args.args, ['partner', 1],
                        'The route to get google drive config should have been called');
                    return $.when([{id: 27, name: 'Cyberdyne Systems'}]);
                }
                if (route === '/web/dataset/call_kw/google.drive.config/search_read'){
                    return $.when([{google_drive_resource_id: "T1000",
                                    google_drive_client_id: "cyberdyne.org",
                                    id: 1}]);
                }
                if (route === '/web/dataset/call_kw/google.drive.config/get_google_drive_url') {
                    assert.deepEqual(args.args, [27, self.activeId, 'T1000'],
                        'The route to get the Google url should have been called');
                    // We don't return anything useful, otherwise it will open a new tab
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
        });

        var nameToId = {
            'Locomotive Breath': 1,
            'Hey Macarena': 2,
        }
        // Trigger opening of the dynamic link
        self.activeId = nameToId[$("[name='display_name']").text()];
        form.sidebar.$('.oe_share_gdoc').find('a:first').click();
        form.pager.$('.o_pager_next').click();
        self.activeId = nameToId[$("[name='display_name']").text()];
        form.sidebar.$('.oe_share_gdoc').find('a:first').click();
        form.destroy();
    });
});

});
