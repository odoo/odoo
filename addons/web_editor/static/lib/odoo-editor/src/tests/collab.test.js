import { OdooEditor as Editor } from '../editor.js';
import { parseTextualSelection, setSelection } from './utils.js';

const getIncomingStep = (previousStepId, id = '328e7db4-6abf-48e5-88de-2ac505323735') => ({
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
    id,
    userId: '268d771b-4467-4963-98e3-707c7d05501c',
    previousStepId,
});

const testCommandSerialization = (content, commandCb) => {
    const editable = document.createElement('div');
    editable.innerHTML = content;
    document.body.appendChild(editable);
    const selection = parseTextualSelection(editable);

    const receivingNode = document.createElement('div');
    document.body.appendChild(receivingNode);

    const receivingEditor = new Editor(receivingNode, {
        toSanitize: false,
        collaborative: {
            send: () => {},
            requestSynchronization: () => {},
        },
    });
    if (selection) {
        setSelection(selection);
    } else {
        document.getSelection().removeAllRanges();
    }
    const editor = new Editor(editable, {
        toSanitize: false,
        collaborative: {
            send: s => {
                receivingEditor.historyReceive(s);
            },
        },
    });
    editor.keyboardType = 'PHYSICAL_KEYBOARD';
    receivingEditor.historySynchronise(editor.historyGetSnapshot());
    commandCb(editor);
    window.chai.expect(editable.innerHTML).to.equal(receivingNode.innerHTML);
};

describe('Collaboration', () => {
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
        it('should reorder steps on incoming conflict (incoming before local)', () => {
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

            const incomingStep = getIncomingStep(editor._historySteps[0].id, 'a');
            const historyStepsBeforeReceive = [...editor._historySteps];
            // Take everything but the "init" step.
            const existingSteps = editor._historySteps.slice(1);
            existingSteps[0].id = 'b';
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
        it('should reorder steps on incoming conflict (local before incoming)', () => {
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
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            editor.execCommand('insertHTML', '<b>foo</b>');
            sendSpy.resetHistory();
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            const incomingStep = getIncomingStep(editor._historySteps[0].id, 'b');
            const historyStepsBeforeReceive = [...editor._historySteps];
            // Take everything but the "init" step.
            const existingSteps = editor._historySteps.slice(1);
            existingSteps[0].id = 'a';
            editor.historyReceive(incomingStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai
                .expect(historyApplySpy.getCall(0).firstArg)
                .to.deep.equal(existingSteps[0].mutations);
            existingSteps.forEach((step, i) => {
                // getCall i + 1 because of the new step that is applied first
                window.chai
                    .expect(historyApplySpy.getCall(i).firstArg, 'should have reapplied step')
                    .to.deep.equal(step.mutations);
            });
            window.chai.expect(historyRevertSpy.getCall(0).firstArg).to.be.equal(existingSteps[0]);
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai
                .expect(editor._historySteps.map(({ id }) => id))
                .to.deep.equal([
                    historyStepsBeforeReceive.shift().id,
                    ...existingSteps.map(({ id }) => id),
                    incomingStep.id,
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
    describe('snapshot', () => {
        it('should make a snaphshot that represents the entire document', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const editor = new Editor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: () => {},
                    requestSynchronization: () => {},
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            editor.execCommand('insertHTML', '<b>foo</b>');
            editor.execCommand('insertHTML', '<b>bar</b>');
            editor.execCommand('insertHTML', '<b>baz</b>');

            const snap = editor.historyGetSnapshot();
            const virtualNode = document.createElement('div');

            const secondEditor = new Editor(virtualNode, {
                toSanitize: false,
                collaborative: {
                    send: () => {},
                    requestSynchronization: () => {},
                },
            });
            secondEditor.historySynchronise(snap);
            var origIt = document.createNodeIterator(testNode);
            var destIt = document.createNodeIterator(virtualNode);
            var res;
            do {
                res = [origIt.nextNode(), destIt.nextNode()];
                window.chai.expect(res[0] && res[0].oid).to.eql(res[1] && res[1].oid);
            } while (res[0] && res[1]);
            window.chai.expect(testNode.innerHTML).to.equal(virtualNode.innerHTML);
        });
    });
    describe('serialization', () => {
        it('should serialize insertText correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertText', 'abc');
            });
        });

        it('should serialize insertFontAwesome correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertFontAwesome', 'fa fa-pastafarianism');
            });
        });

        it('should serialize undo correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertText', 'abc');
                editor.execCommand('undo');
            });
        });

        it('should serialize redo correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertText', 'abc');
                editor.execCommand('undo');
                editor.execCommand('redo');
            });
        });

        it('should serialize setTag correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('setTag', 'p');
            });
        });

        it('should serialize bold correctly', () => {
            testCommandSerialization('<p>[Ah.]</p>', editor => {
                editor.execCommand('bold');
            });
        });

        it('should serialize italic correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('italic');
            });
        });

        it('should serialize underline correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('underline');
            });
        });

        it('should serialize strikeThrough correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('strikeThrough');
            });
        });

        it('should serialize removeFormat correctly', () => {
            testCommandSerialization(
                '<p><span style="font-weight: bold;">[Ah.]</span></p>',
                editor => {
                    editor.execCommand('removeFormat');
                },
            );
        });

        it('should serialize justifyLeft correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyLeft');
            });
        });

        it('should serialize justifyRight correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyRight');
            });
        });

        it('should serialize justifyCenter correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyCenter');
            });
        });

        it('should serialize justifyFull correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyFull');
            });
        });

        it('should serialize setFontSize correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('setFontSize', '3em');
            });
        });

        it('should serialize createLink correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('createLink', 'https://example.com', 'example');
            });
        });

        it('should serialize unlink correctly', () => {
            testCommandSerialization(
                '<h3><a href="https://example.com">example[]</a></h3>',
                editor => {
                    editor.execCommand('unlink');
                },
            );
        });

        it('should serialize indentList correctly', () => {
            testCommandSerialization('<ul><li>Ah.[]</li></ul>', editor => {
                editor.execCommand('indentList');
            });
        });

        it('should serialize toggleList correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('toggleList');
            });
        });

        it('should serialize applyColor correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('applyColor', '#F00', 'color');
            });
        });

        it('should serialize insertTable correctly', () => {
            testCommandSerialization('<p>Ah.[]</p>', editor => {
                editor.execCommand('insertTable', { rowNumber: 2, colNumber: 2 });
            });
        });

        it('should serialize addColumnLeft correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addColumnLeft');
                },
            );
        });

        it('should serialize addColumnRight correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addColumnRight');
                },
            );
        });

        it('should serialize addRowAbove correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addRowAbove');
                },
            );
        });

        it('should serialize addRowBelow correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addRowBelow');
                },
            );
        });

        it('should serialize removeColumn correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('removeColumn');
                },
            );
        });

        it('should serialize removeRow correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('removeRow');
                },
            );
        });

        it('should serialize deleteTable correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('deleteTable');
                },
            );
        });

        it('should serialize insertHorizontalRule correctly', () => {
            testCommandSerialization('<p>Ah.[]</p>', editor => {
                editor.execCommand('insertHorizontalRule');
            });
        });

        it('should serialize oEnter correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('oEnter');
            });
        });
        it('should serialize oShiftEnter correctly', () => {
            testCommandSerialization('<p>[]<br></p>', editor => {
                editor.execCommand('oShiftEnter');
            });
        });
        it('should serialize insertHtml correctly', () => {
            testCommandSerialization('<p>[test]<br></p>', editor => {
                editor.execCommand('insertHTML', '<b>lol</b>');
            });
        });
    });
});
