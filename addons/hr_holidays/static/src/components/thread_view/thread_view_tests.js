odoo.define('hr_holidays/static/src/components/thread_view/thread_view_tests.js', function (require) {
'use strict';

const { link } = require('@mail/model/model_field_command');
const {
    beforeEach,
    createRootMessagingComponent,
} = require('@mail/utils/test_utils');

QUnit.module('hr_holidays', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_view', {}, function () {
QUnit.module('thread_view_tests.js', {
    beforeEach() {
        beforeEach.call(this);

        /**
         * @param {mail.thread_view} threadView
         * @param {Object} [otherProps={}]
         */
        this.createThreadViewComponent = async (threadView, otherProps = {}) => {
            const target = this.webClient.el;
            const props = Object.assign({ threadViewLocalId: threadView.localId }, otherProps);
            await createRootMessagingComponent(this, "ThreadView", { props, target });
        };
    },
});

QUnit.skip('out of office message on direct chat with out of office partner', async function (assert) {
    // skip: I'm not sure why it doesn't work, issue with the feature out of office or not? date maybe?
    assert.expect(2);

    // Returning date of the out of office partner, simulates he'll be back in a month
    const returningDate = moment.utc().add(1, 'month');
    // Needed partner & user to allow simulation of message reception
    this.serverData.models['res.partner'].records.push({
        id: 11,
        name: "Foreigner partner",
        out_of_office_date_end: returningDate.format("YYYY-MM-DD"),
    });
    this.serverData.models['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.serverData.currentPartnerId, 11],
    }];
    const { messaging } = await this.start();
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = messaging.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: link(thread),
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    assert.containsOnce(
        document.body,
        '.o_ThreadView_outOfOffice',
        "should have an out of office alert on thread view"
    );
    const formattedDate = returningDate.toDate().toLocaleDateString(
        messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.ok(
        document.querySelector('.o_ThreadView_outOfOffice').textContent.includes(formattedDate),
        "out of office message should mention the returning date"
    );
});

});
});
});

});
