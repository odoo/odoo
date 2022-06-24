import { BasicEditor, testEditor } from '../utils.js';

const timeoutPromise = ms =>
    new Promise(resolve => {
        setTimeout(() => resolve(), ms);
    });

const appendSpan = (element, id = 1) => {
    // The ID is necessary to prevent the editor to merge elements together:
    // If multiple spans are sibblings and nothing differentiates them,
    // the Editor will try to merge them.
    const span = document.createElement('SPAN');
    span.id = 'id-' + id;
    span.textContent = '*';
    element.append(span);
};

describe('Autostep', () => {
    it('should record a change not made through the editor itself', async function () {
        this.slow(600);
        await testEditor(BasicEditor, {
            contentBefore: '<p>a[]</p>',
            stepFunction: async editor => {
                const originalHistoryLength = editor._historySteps.length;

                // Wait for some plugin (e.g. QWEB) that currently use a
                // setTimeout in order to wait for the editable to be inserted
                // in the DOM to perform logic that reset the autostep timeout.
                await timeoutPromise(20);

                appendSpan(editor.editable.querySelector('p'));
                await timeoutPromise(20).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength,
                    );
                });
                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength + 1,
                        'There is 1 more step in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span id="id-1">*</span></p>',
        });
    });
    it('should not record a change not made through the editor itself', async function () {
        this.slow(600);
        await testEditor(BasicEditor, {
            contentBefore: '<p>a[]</p>',
            stepFunction: async editor => {
                editor.automaticStepUnactive('test');
                const originalHistoryLength = editor._historySteps.length;
                appendSpan(editor.editable.querySelector('p'));
                await timeoutPromise(20).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength,
                    );
                });
                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength,
                        'There is not more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span id="id-1">*</span></p>',
        });
    });
    it('should record changes not made through the editor itself once reactivated', async function () {
        this.slow(600);
        await testEditor(BasicEditor, {
            contentBefore: '<p>a[]</p>',
            stepFunction: async editor => {
                const originalHistoryLength = editor._historySteps.length;

                // Wait for some plugin (e.g. QWEB) that currently use a
                // setTimeout in order to wait for the editable to be inserted
                // in the DOM to perform logic that reset the autostep timeout.
                await timeoutPromise(20);

                editor.automaticStepUnactive('test');
                appendSpan(editor.editable.querySelector('p'), 1);
                editor.automaticStepActive('test');
                appendSpan(editor.editable.querySelector('p'), 2);

                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength + 1,
                        'There is 1 more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span id="id-1">*</span><span id="id-2">*</span></p>',
        });
    });
    it('should record a change not made through the editor itself if not everyone has reactivated autostep', async function () {
        this.slow(600);
        await testEditor(BasicEditor, {
            contentBefore: '<p>a[]</p>',
            stepFunction: async editor => {
                const originalHistoryLength = editor._historySteps.length;
                editor.automaticStepUnactive('test');
                editor.automaticStepUnactive('test2');
                appendSpan(editor.editable.querySelector('p'), 1);
                editor.automaticStepActive('test');

                appendSpan(editor.editable.querySelector('p'), 2);

                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength,
                        'There is not more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span id="id-1">*</span><span id="id-2">*</span></p>',
        });
    });

    it('should record a change not made through the editor itself if everyone has reactivated autostep', async function () {
        this.slow(600);
        await testEditor(BasicEditor, {
            contentBefore: '<p>a[]</p>',
            stepFunction: async editor => {
                const originalHistoryLength = editor._historySteps.length;

                // Wait for some plugin (e.g. QWEB) that currently use a
                // setTimeout in order to wait for the editable to be inserted
                // in the DOM to perform logic that reset the autostep timeout.
                await timeoutPromise(20);

                editor.automaticStepUnactive('test');
                editor.automaticStepUnactive('test2');
                appendSpan(editor.editable.querySelector('p'), 1);
                editor.automaticStepActive('test');
                appendSpan(editor.editable.querySelector('p'), 2);
                editor.automaticStepActive('test2');
                appendSpan(editor.editable.querySelector('p'), 3);

                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength + 1,
                        'There is 1 more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span id="id-1">*</span><span id="id-2">*</span><span id="id-3">*</span></p>',
        });
    });
});
