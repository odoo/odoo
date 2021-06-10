import { OdooEditor as Editor } from '../editor.js';

const getIncomingStep = previousStepId => ({
    cursor: { anchorNode: 1, anchorOffset: 2, focusNode: 1, focusOffset: 2 },
    mutations: [
        {
            type: 'add',
            append: 1,
            id: '199bee91-e88e-4681-a2f7-54ec8fe6fe3c',
            node: {
                nodeType: 1,
                oid: '199bee91-e88e-4681-a2f7-54ec8fe6fe3c',
                tagName: 'B',
                children: [
                    {
                        nodeType: 3,
                        oid: '76498319-5fea-4fda-abf9-9cbd10a279f8',
                        textValue: 'foo',
                    },
                ],
                attributes: {},
            },
        },
    ],
    id: '328e7db4-6abf-48e5-88de-2ac505323735',
    userId: '268d771b-4467-4963-98e3-707c7d05501c',
    previousStepId,
});

describe.only('Collaboration', () => {
    describe('Receive step', () => {
        it('should apply a step when receving a step that is not in the history yet', () => {
            const testNode = document.createElement('div');
            testNode.setAttribute('contenteditable', 'true');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new Editor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                    initServerHistory: () => {},
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            const incomingStep = getIncomingStep(editor._historySteps[0].id);
            const historyStepsBeforeReceive = [...editor._historySteps];
            editor.historyReceive(incomingStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(0);
            window.chai.expect(sendSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai
                .expect(historyApplySpy.getCall(0).firstArg)
                .to.deep.equal(incomingStep.mutations);
            window.chai.expect(historyRevertSpy.callCount).to.equal(0);
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai
                .expect(editor._historySteps)
                .to.deep.equal([...historyStepsBeforeReceive, incomingStep]);
        });
        it('should revert and reapply the history if it receives a step where the index does not match the current history', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new Editor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                    initServerHistory: () => {},
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            editor.execCommand('insertHTML', '<b>foo</b>');
            editor.execCommand('insertHTML', '<b>bar</b>');
            editor.execCommand('insertHTML', '<b>baz</b>');
            sendSpy.resetHistory();
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            const incomingStep = getIncomingStep(editor._historySteps[0].id);
            const historyStepsBeforeReceive = [...editor._historySteps];
            // Take everything but the "init" step.
            const existingSteps = editor._historySteps.slice(1);
            const incomingSecondStep = { ...incomingStep };
            editor.historyReceive(incomingSecondStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai
                .expect(historyApplySpy.getCall(0).firstArg)
                .to.deep.equal(incomingStep.mutations);
            existingSteps.forEach((step, i) => {
                // getCall i + 1 because of the new step that is applied first
                window.chai
                    .expect(historyApplySpy.getCall(i + 1).firstArg, 'should have reapplied step')
                    .to.deep.equal(step.mutations);
                window.chai
                    .expect(
                        historyRevertSpy.getCall(2 - i).firstArg,
                        'should have reverted steps in the inverse apply order',
                    )
                    .to.be.equal(step);
            });
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai
                .expect(editor._historySteps.map(({ id }) => id))
                .to.deep.equal([
                    historyStepsBeforeReceive.shift().id,
                    incomingSecondStep.id,
                    ...existingSteps.map(({ id }) => id),
                ]);
        });
        it('should request a synchronization if it receives a step it can not apply', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new Editor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                    initServerHistory: () => {},
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            // Impossible previousStepId. Real life scenario would be the uuid
            // of a step generated by another client that somehow was not
            // transmitted
            const incomingStep = getIncomingStep('42');
            const historyStepsBeforeReceive = [...editor._historySteps];
            const incoming6thStep = { ...incomingStep, index: 5 };
            editor.historyReceive(incoming6thStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(1);
            window.chai.expect(sendSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai.expect(historyApplySpy.callCount).to.equal(0);
            window.chai.expect(historyRevertSpy.callCount).to.equal(0);
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai.expect(editor._historySteps).to.deep.equal(historyStepsBeforeReceive);
        });
    });
});
