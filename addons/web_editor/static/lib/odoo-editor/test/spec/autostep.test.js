import { BasicEditor, testEditor } from '../utils.js';

const timeoutPromise = ms =>
    new Promise(resolve => {
        setTimeout(() => resolve(), ms);
    });

const appendSpan = element => {
    const span = document.createElement('SPAN');
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
            contentAfter: '<p>a[]<span></span></p>',
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
            contentAfter: '<p>a[]<span></span></p>',
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
                appendSpan(editor.editable.querySelector('p'));
                editor.automaticStepActive('test');
                appendSpan(editor.editable.querySelector('p'));

                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength + 1,
                        'There is 1 more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span></span><span></span></p>',
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
                appendSpan(editor.editable.querySelector('p'));
                editor.automaticStepActive('test');

                appendSpan(editor.editable.querySelector('p'));

                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength,
                        'There is not more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span></span><span></span></p>',
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
                appendSpan(editor.editable.querySelector('p'));
                editor.automaticStepActive('test');
                appendSpan(editor.editable.querySelector('p'));
                editor.automaticStepActive('test2');
                appendSpan(editor.editable.querySelector('p'));

                await timeoutPromise(120).then(() => {
                    window.chai.assert.strictEqual(
                        editor._historySteps.length,
                        originalHistoryLength + 1,
                        'There is 1 more steps in the history',
                    );
                });
            },
            contentAfter: '<p>a[]<span></span><span></span><span></span></p>',
        });
    });
});
