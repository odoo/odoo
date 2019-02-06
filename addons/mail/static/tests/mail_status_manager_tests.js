odoo.define('mail.mailStatusServiceTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var core = require('web.core');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;

QUnit.module('mail', {}, function () {
QUnit.module('service', {}, function () {
QUnit.module('Status manager', {
    beforeEach: function () {
        this.services = mailTestUtils.getMailServices(this);
        this.timeoutMock = mailTestUtils.patchMailTimeouts();
    },
});
QUnit.test('simple set im_status', function (assert) {
    assert.expect(1);
    var parent = testUtils.createParent({
        services: this.services,
        mockRPC: function (route, args) {
            if (route === '/mail/init_messaging') {
                return this._super.apply(this, arguments);
            }
            throw new Error(_.str.sprintf('No rpc call should be performed: %s, %s \n %s', args.model, args.method, route));
        },
    });
    parent.call('mail_service', 'updateImStatus', [{
        id: 1,
        im_status: 'online',
    }]);
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 1 }), 'online');

    this.timeoutMock.runPendingTimeouts();
    parent.destroy();
});

QUnit.test('multi get_im_status', function (assert) {
    assert.expect(9);
    var readCount = 0;
    var parent = testUtils.createParent({
        //data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (route === '/mail/init_messaging') {
                return this._super.apply(this, arguments);
            }
            if (args.method === 'read' && args.model === 'res.partner') {
                assert.deepEqual(args.args[0], [2,3]);
                assert.deepEqual(args.args[1], ['id', 'im_status']);
                readCount++;
                return $.when([
                    {id: 2, im_status: 'away'},
                    {id: 3, im_status: 'im_partner'}
                ]);
            }
            throw new Error(_.str.sprintf('No rpc call should be performed: %s, %s \n %s', args.model, args.method, route));
        },
    });
    parent.call('mail_service', 'updateImStatus', [{
        id: 1,
        im_status: 'online',
    }]);
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 1 }), 'online');
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 2 }), undefined);
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 3 }), undefined);

    this.timeoutMock.runPendingTimeouts();
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 1 }), 'online');
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 2 }), 'away');
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 3 }), 'im_partner');

    this.timeoutMock.runPendingTimeouts();
    assert.strictEqual(readCount, 1, 'Only one read on partner should have been performed');

    parent.destroy();
});

QUnit.test('update loop', function (assert) {
    assert.expect(12);
    var readCount = 0;
    var parent = testUtils.createParent({
        services: this.services,
        mockRPC: function (route, args) {
            if (route === '/mail/init_messaging') {
                return this._super.apply(this, arguments);
            }
            if (args.method === 'read' && args.model === 'res.partner') {
                assert.deepEqual(args.args[0], [1, 2]);
                assert.deepEqual(args.args[1], ['id', 'im_status']);
                readCount++;
                return $.when([
                    {"id": 1, "im_status": "online"},
                    {"id": 2, "im_status": "away"}
                ]);
            }
            throw new Error(_.str.sprintf('No rpc call should be performed: %s, %s \n %s', args.model, args.method, route));
        },
    });
    // set initial status
    parent.call('mail_service', 'updateImStatus', [
        { id: 1, im_status: 'offline' },
        { id: 2, im_status: 'offline' },
        { id: 3, im_status: 'im_partner' }, //shouldn't be updated !!!!
    ]);
    //_updateImStatusLoop should be running at one second per iteration, lets make a minute pass.
    assert.strictEqual(readCount, 0);
    this.timeoutMock.addTime(50*1000);
    assert.strictEqual(readCount, 0);
    this.timeoutMock.addTime(1000);
    assert.strictEqual(readCount, 1, 'one call should have been made after 50 seconds' );
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 1 }), 'online');
    assert.strictEqual(parent.call('mail_service', 'getImStatus', { partnerID: 2 }), 'away');

    //simulate change of focus
    //original listener:  $(window).on("blur", this._onWindowFocusChange.bind(this, false); + unload, ...
    parent.call('mail_service', '_onWindowFocusChange', false); // remove focus from tab

    this.timeoutMock.addTime(5*60*1000); // x minutes without focus, no rpc should be done during this time
    assert.strictEqual(readCount, 1, 'No more call should have been performed');
    //simulate change of focus
    //original listener:  $(window).on("focus", this._onWindowFocusChange.bind(this, true);
    parent.call('mail_service', '_onWindowFocusChange', true); // give focus to tab
    var nextUpdateDelay = this.timeoutMock.getNextTimeoutDelay();
    assert.strictEqual(nextUpdateDelay, 1000, "next update should be done in maximum one second");
    this.timeoutMock.addTime(nextUpdateDelay); // one second should be enough
    assert.strictEqual(readCount, 2, 'One more call should have been done once tab focused');
    this.timeoutMock.runPendingTimeouts();
    parent.destroy();
});

QUnit.test('update status', function (assert) {
    // the current solution to look for updatable im_status in dom is not perfect, but waiting for
    // ability to include widgets in views, this is the most simple solution
    assert.expect(2);
    var StatusWidget = Widget.extend({
        start: function () {
            this.render();
            this._super.apply(this, arguments);
        },
        render: function () {
            var status = QWeb.render('mail.UserStatus', {
                status: 'online',
                partnerID: 1,
            });
            this.$el.html(status);
        }
    });
    var statusWidget = new StatusWidget();
    testUtils.mock.addMockEnvironment(statusWidget, {
        services: this.services,
        mockRPC: function (route, args) {
            if (route === '/mail/init_messaging') {
                return this._super.apply(this, arguments);
            }
            throw new Error(_.str.sprintf('No rpc call should be performed: %s, %s \n %s', args.model, args.method, route));
        },
    });
    statusWidget.appendTo($('#qunit-fixture'));
    //Render unknow im_status:
    // set initial status
    assert.ok(statusWidget.$('.o_updatable_im_status i').hasClass('o_user_online'));

    statusWidget.call('mail_service', 'updateImStatus', [
        { id: 1, im_status: 'offline' },
    ]);
    assert.notOk(statusWidget.$('.o_updatable_im_status i').hasClass('o_user_online'));
    this.timeoutMock.runPendingTimeouts();
    statusWidget.destroy();
});

});
});
});
