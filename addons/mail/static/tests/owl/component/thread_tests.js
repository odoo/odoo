odoo.define('mail.component.ThreadTests', function (require) {
"use strict";

const Thread = require('mail.component.Thread');
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    dragoverFiles,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Thread', {
    beforeEach() {
        utilsBeforeEach(this);

        /**
         * @param {string} threadLocalId
         * @param {Object} [otherProps]
         */
        this.createThread = async (threadLocalId, otherProps) => {
            const env = await this.widget.call('env', 'get');
            this.thread = new Thread(env, {
                threadLocalId,
                ...otherProps,
            });
            await this.thread.mount(this.widget.$el[0]);
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { store, widget } = await utilsStart({
                ...params,
                data: this.data,
            });
            this.store = store;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.thread) {
            this.thread.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.store = undefined;
    }
});

QUnit.test('dragover files on thread with composer', async function (assert) {
    assert.expect(1);

    await this.start();
    const threadLocalId = this.store.dispatch('_createThread', {
        channel_type: 'channel',
        id: 100,
        members: [
            {
                email: "john@example.com",
                id: 9,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            }
        ],
        name: "General",
        public: 'public',
    });
    await this.createThread(threadLocalId, {
        hasComposer: true,
    });
    await dragoverFiles(document.querySelector('.o_Thread'));
    assert.ok(
        document.querySelector('.o_Composer_dropZone'),
        "should have dropzone when dragging file over the thread");

});

});
});
});
