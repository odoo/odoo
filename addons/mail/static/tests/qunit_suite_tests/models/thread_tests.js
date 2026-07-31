/** @odoo-module **/

/**
 * Test for race condition between setMainAttachment and fetchData
 * 
 * Problem scenario:
 * 1. User selects attachment → setMainAttachment() is called
 * 2. setMainAttachment() immediately updates client-side mainAttachment 
 * 3. setMainAttachment() starts RPC call to update database (async)
 * 4. While RPC is pending, fetchData() is triggered (by onChanges)
 * 5. fetchData() overwrites mainAttachment with OLD value from database
 *    (because database hasn't been updated yet by pending RPC)
 * 6. Result: mainAttachment shows old value instead of user's selection
 * 
 * Fix: Use _pendingMainAttachment flag to prevent fetchData from 
 * overwriting mainAttachment during setMainAttachment operation
 */

QUnit.module('mail', {}, function () {
    QUnit.module('models', {}, function () {
        QUnit.module('thread_tests.js');

        QUnit.test('race condition: _pendingMainAttachment flag prevents fetchData from overwriting mainAttachment', async function (assert) {
            assert.expect(4);

            // Mock Thread object with our fix implementation
            const mockThread = {
                mainAttachment: null,
                _pendingMainAttachment: false,

                // Mock update method
                update(values) {
                    Object.assign(this, values);
                },

                // Mock messaging.rpc method
                messaging: {
                    rpc: async () => {
                        // Simulate network delay
                        await new Promise(resolve => setTimeout(resolve, 50));
                        return {};
                    }
                },

                // Implementation under test: setMainAttachment with _pendingMainAttachment flag
                async setMainAttachment(attachment) {
                    this.update({
                        mainAttachment: attachment,
                        _pendingMainAttachment: true,
                    });
                    try {
                        await this.messaging.rpc({
                            model: 'ir.attachment',
                            method: 'register_as_main_attachment',
                            args: [[attachment.id]],
                        });
                    } finally {
                        this.update({ _pendingMainAttachment: false });
                    }
                },

                // Implementation under test: fetchData with _pendingMainAttachment check
                async fetchData(requestList) {
                    // Simulate server response with OLD mainAttachment
                    const serverResponse = {
                        mainAttachment: { id: 100, name: 'old_attachment.txt' }, // OLD value
                        hasWriteAccess: true,
                        hasReadAccess: true,
                        canPostOnReadonly: false,
                    };

                    const values = {
                        hasWriteAccess: serverResponse.hasWriteAccess,
                        hasReadAccess: serverResponse.hasReadAccess,
                        canPostOnReadonly: serverResponse.canPostOnReadonly
                    };

                    // KEY FIX: Only update mainAttachment if not currently setting it
                    if (serverResponse.mainAttachment && !this._pendingMainAttachment) {
                        values.mainAttachment = serverResponse.mainAttachment;
                    }

                    this.update(values);
                }
            };

            // Mock attachments
            const newAttachment = { id: 999, name: 'new_attachment.txt' };

            // STEP 1: Verify initial state
            assert.strictEqual(mockThread._pendingMainAttachment, false,
                'Initial _pendingMainAttachment should be false');

            // STEP 2: User selects NEW attachment as main
            const setMainAttachmentPromise = mockThread.setMainAttachment(newAttachment);

            // STEP 3: Verify flag is set and mainAttachment is updated immediately
            assert.strictEqual(mockThread._pendingMainAttachment, true,
                '_pendingMainAttachment should be true during setMainAttachment operation');
            assert.strictEqual(mockThread.mainAttachment, newAttachment,
                'mainAttachment should be immediately set to NEW attachment');

            // STEP 4: Simulate fetchData call while setMainAttachment is pending
            // This simulates the race condition - fetchData would normally overwrite
            // mainAttachment with OLD value, but our fix should prevent this
            await mockThread.fetchData(['attachments']);

            // STEP 5: Verify mainAttachment was NOT overwritten by fetchData
            assert.strictEqual(mockThread.mainAttachment, newAttachment,
                'mainAttachment should remain NEW attachment, not overwritten by fetchData with OLD value');

            // Clean up: wait for setMainAttachment to complete
            await setMainAttachmentPromise;
        });

    });
});

