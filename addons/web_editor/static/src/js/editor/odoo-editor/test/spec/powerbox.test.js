import { setSelection } from '../../src/OdooEditor.js';
import { Powerbox } from '../../src/powerbox/Powerbox.js';
import { BasicEditor, _isMobile, insertText, nextTick, testEditor, triggerEvent } from '../utils.js';

const getCurrentCommandNames = powerbox => {
    return [...powerbox.el.querySelectorAll('.oe-powerbox-commandName')].map(c => c.innerText);
}

describe('Powerbox', () => {
    describe('integration', () => {
        it('should open the Powerbox on type `/`', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]</p>',
                stepFunction: async editor => {
                    window.chai.expect(editor.powerbox.isOpen).to.eql(false);
                    window.chai.expect(editor.powerbox.el.style.display).to.eql('none');
                    await insertText(editor, '/');
                    window.chai.expect(editor.powerbox.isOpen).to.eql(true);
                    window.chai.expect(editor.powerbox.el.style.display).not.to.eql('none');
                },
            });
        });
        it('should filter the Powerbox contents with term', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]</p>',
                stepFunction: async editor => {
                    await insertText(editor, '/');
                    await insertText(editor, 'head');
                    await triggerEvent(editor.editable, 'keyup');
                    window.chai.expect(getCurrentCommandNames(editor.powerbox)).to.eql(['Heading 1', 'Heading 2', 'Heading 3']);
                },
            });
        });
        it('should not filter the powerbox contents when collaborator type on two different blocks', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab</p><p>c[]d</p>',
                stepFunction: async editor => {
                    await insertText(editor, '/');
                    await insertText(editor, 'heading');
                    setSelection(editor.editable.firstChild, 1);
                    window.chai.expect(editor.powerbox.isOpen).to.be.true;
                    // Mimick a collaboration scenario where another user types
                    // random text, using `insert` as it won't trigger keyup.
                    editor.execCommand('insert', 'random text');
                    window.chai.expect(editor.powerbox.isOpen).to.be.true;
                    setSelection(editor.editable.lastChild, 9);
                    window.chai.expect(editor.powerbox.isOpen).to.be.true;
                    await insertText(editor, '1');
                    window.chai.expect(editor.powerbox.isOpen).to.be.true;
                    window.chai.expect(getCurrentCommandNames(editor.powerbox)).to.eql(['Heading 1']);
                },
            });
        });
        it('should execute command and remove term and hot character on Enter', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]</p>',
                stepFunction: async editor => {
                    editor.powerbox.el.classList.add('yo');
                    await insertText(editor, '/');
                    await insertText(editor, 'head');
                    await triggerEvent(editor.editable, 'keyup');
                    await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                },
                contentAfter: '<h1>ab[]</h1>',
            });
        });
        it('should not reinsert the selected text after command validation', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await insertText(editor, 'abc');
                    const p = editor.editable.querySelector('p');
                    setSelection(p.firstChild, 0, p.lastChild, 1);
                    await nextTick();
                    await insertText(editor, '/');
                    window.chai.expect(editor.powerbox.isOpen).to.be.true;
                    await insertText(editor, 'h1');
                    await triggerEvent(editor.editable, "keydown", { key: "Enter" });
                },
                contentAfter: '<h1>[]<br></h1>',
            });
        });
        it('should close the powerbox if keyup event is called on other block', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab</p><p>c[]d</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, '/');
                    window.chai.expect(editor.powerbox.isOpen).to.be.true;
                    setSelection(editor.editable.firstChild, 1);
                    await triggerEvent(editor.editable, 'keyup');
                    window.chai.expect(editor.powerbox.isOpen).to.be.false;
                },
            });
        });
    });
    it('should insert a 3x3 table on type `/table` in mobile view', async () => {
        if(_isMobile()){
            await testEditor(BasicEditor, {
                contentBefore: `<p>[]<br></p>`,
                stepFunction: async editor => {
                    await insertText(editor,'/');
                    await insertText(editor, 'table');
                    await triggerEvent(editor.editable,'keyup');
                    await triggerEvent(editor.editable,'keydown', {key: 'Enter'});
                },
                contentAfter: `<table class="table table-bordered o_table"><tbody><tr><td>[]<p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr></tbody></table><p><br></p>`,
            });
        }
    });
    describe('class', () => {
        it('should properly order default commands and categories', async () => {
            const editable = document.createElement('div');
            document.body.append(editable);
            const powerbox = new Powerbox({
                categories: [
                    {name: 'a', priority: 2},
                    {name: 'b', priority: 4},
                    {name: 'c', priority: 1}, // redefined lower -> ignore
                    {name: 'd', priority: 4}, // same as b -> alphabetical
                    {name: 'c', priority: 3},
                ],
                commands: [
                    {category: 'f', name: 'f1'}, // category doesn't exist -> end
                    {category: 'e', name: 'e1'}, // category doesn't exist -> end
                    {category: 'a', name: 'a1', priority: 1},
                    {category: 'a', name: 'a4', priority: 3},
                    {category: 'a', name: 'a2', priority: 3},
                    {category: 'a', name: 'a3', priority: 2},
                    {category: 'b', name: 'b3'}, // no priority -> priority 1
                    {category: 'b', name: 'b1'},
                    {category: 'b', name: 'b2'},
                    {category: 'c', name: 'c1'},
                    {category: 'd', name: 'd1'},
                ],
                editable,
            });
            powerbox.open();
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(
                ['b1', 'b2', 'b3', 'd1', 'c1', 'a2', 'a4', 'a3', 'a1', 'e1', 'f1']
            );
            powerbox.destroy();
            editable.remove();
        });
        it('should navigate through commands with arrow keys', async () => {
            const editable = document.createElement('div');
            document.body.append(editable);
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: '2'},
                    {category: 'a', name: '3'},
                    {category: 'a', name: '1'},
                ],
                editable,
            });
            powerbox.open();
            window.chai.expect(powerbox._context.selectedCommand.name).to.eql('1');
            await triggerEvent(editable, 'keydown', { key: 'ArrowDown'});
            window.chai.expect(powerbox._context.selectedCommand.name).to.eql('2');
            await triggerEvent(editable, 'keydown', { key: 'ArrowDown'});
            window.chai.expect(powerbox._context.selectedCommand.name).to.eql('3');
            await triggerEvent(editable, 'keydown', { key: 'ArrowUp'});
            window.chai.expect(powerbox._context.selectedCommand.name).to.eql('2');
            await triggerEvent(editable, 'keydown', { key: 'ArrowUp'});
            window.chai.expect(powerbox._context.selectedCommand.name).to.eql('1');
            powerbox.destroy();
            editable.remove();
        });
        it('should execute command on press Enter', async () => {
            const editable = document.createElement('div');
            editable.classList.add('odoo-editor-editable');
            document.body.append(editable);
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: '2', callback: () => editable.innerText = '2'},
                    {category: 'a', name: '3', callback: () => editable.innerText = '3'},
                    {category: 'a', name: '1', callback: () => editable.innerText = '1'},
                ],
                editable,
            });
            setSelection(editable, 0);
            powerbox.open();
            window.chai.expect(editable.innerText).to.eql('');
            await triggerEvent(editable, 'keydown', { key: 'Enter'});
            window.chai.expect(editable.innerText).to.eql('1');
            powerbox.open();
            await triggerEvent(editable, 'keydown', { key: 'ArrowDown'});
            await triggerEvent(editable, 'keydown', { key: 'Enter'});
            window.chai.expect(editable.innerText).to.eql('2');
            powerbox.destroy();
            editable.remove();
        });
        it('should filter commands with `commandFilters`', async () => {
            const editable = document.createElement('div');
            document.body.append(editable);
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: 'a2'},
                    {category: 'a', name: 'a3'},
                    {category: 'a', name: 'a1'},
                    {category: 'b', name: 'b2x'},
                    {category: 'b', name: 'b3x'},
                    {category: 'b', name: 'b1y'},
                ],
                editable,
                commandFilters: [commands => commands.filter(command => command.category === 'b')],
            });
            powerbox.open();
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['b1y', 'b2x', 'b3x']);
            powerbox.close();
            powerbox.commandFilters.push(commands => commands.filter(command => command.name.includes('x')))
            powerbox.open();
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['b2x', 'b3x']);
            powerbox.destroy();
            editable.remove();
        });
        it('should filter commands with `isDisabled`', async () => {
            const editable = document.createElement('div');
            document.body.append(editable);
            let disableCommands = false;
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: 'a2', isDisabled: () => disableCommands},
                    {category: 'a', name: 'a3', isDisabled: () => disableCommands},
                    {category: 'a', name: 'a1', isDisabled: () => disableCommands},
                    {category: 'b', name: 'b2x'},
                    {category: 'b', name: 'b3x'},
                    {category: 'b', name: 'b1y'},
                ],
                editable,
            });
            powerbox.open();
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3', 'b1y', 'b2x', 'b3x']);
            powerbox.close();
            disableCommands = true;
            powerbox.open();
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['b1y', 'b2x', 'b3x']);
            powerbox.close();
            disableCommands = false;
            powerbox.open();
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3', 'b1y', 'b2x', 'b3x']);
            powerbox.destroy();
            editable.remove();
        });
        it('should filter commands with filter text', async () => {
            const editable = document.createElement('div');
            editable.classList.add('odoo-editor-editable');
            document.body.append(editable);
            editable.append(document.createTextNode('original text'));
            setSelection(editable.firstChild, 13);
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: 'a2'},
                    {category: 'a', name: 'a3'},
                    {category: 'a', name: 'a1'},
                    {category: 'b', name: 'b2x'},
                    {category: 'b', name: 'b3x'},
                    {category: 'b', name: 'b1y'},
                ],
                editable,
            });
            powerbox.open();
            window.chai.expect(powerbox._context.initialValue).to.eql('original text');
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3', 'b1y', 'b2x', 'b3x']);
            // filter: '1'
            editable.append(document.createTextNode('1'));
            await triggerEvent(editable, 'keyup');
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'b1y']);
            // filter: ''
            editable.lastChild.remove();
            await triggerEvent(editable, 'keyup');
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3', 'b1y', 'b2x', 'b3x']);
            // filter: 'a'
            editable.append(document.createTextNode('a'));
            await triggerEvent(editable, 'keyup'); // filter: 'a'.
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3']);
            editable.append(document.createTextNode('1'));
            await triggerEvent(editable, 'keyup'); // filter: 'a1'.
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1']);
            powerbox.destroy();
            editable.remove();
        });
        it('should close the Powerbox on remove last filter text with Backspace', async () => {
            const editable = document.createElement('div');
            editable.classList.add('odoo-editor-editable');
            document.body.append(editable);
            editable.append(document.createTextNode('1'));
            setSelection(editable.firstChild, 13);
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: 'a2'},
                    {category: 'a', name: 'a3'},
                    {category: 'a', name: 'a1'},
                    {category: 'b', name: 'b2x'},
                    {category: 'b', name: 'b3x'},
                    {category: 'b', name: 'b1y'},
                ],
                editable,
            });
            powerbox.open();
            // Text: '1'
            window.chai.expect(powerbox._context.initialValue).to.eql('1');
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3', 'b1y', 'b2x', 'b3x']);
            // Text: '1y' -> filter: 'y'
            editable.append(document.createTextNode('x'));
            await triggerEvent(editable, 'keyup');
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['b2x', 'b3x']);
            // Text: '1'
            editable.lastChild.remove();
            await triggerEvent(editable, 'keydown', { key: 'Backspace' });
            await triggerEvent(editable, 'keyup');
            window.chai.expect(getCurrentCommandNames(powerbox)).to.eql(['a1', 'a2', 'a3', 'b1y', 'b2x', 'b3x']);
            window.chai.expect(powerbox.isOpen).to.eql(true);
            window.chai.expect(powerbox.el.style.display).not.to.eql('none');
            // Text: ''
            editable.lastChild.remove();
            await triggerEvent(editable, 'keydown', { key: 'Backspace' });
            await triggerEvent(editable, 'keyup');
            window.chai.expect(powerbox.isOpen).to.eql(false);
            window.chai.expect(powerbox.el.style.display).to.eql('none');
            powerbox.destroy();
            editable.remove();
        });
        it('should close the Powerbox on press Escape', async () => {
            const editable = document.createElement('div');
            document.body.append(editable);
            const powerbox = new Powerbox({
                categories: [],
                commands: [
                    {category: 'a', name: '2'},
                    {category: 'a', name: '3'},
                    {category: 'a', name: '1'},
                ],
                editable,
            });
            powerbox.open();
            window.chai.expect(powerbox.isOpen).to.eql(true);
            window.chai.expect(powerbox.el.style.display).not.to.eql('none');
            await triggerEvent(editable, 'keydown', { key: 'Escape' });
            window.chai.expect(powerbox.isOpen).to.eql(false);
            window.chai.expect(powerbox.el.style.display).to.eql('none');
            powerbox.destroy();
            editable.remove();
        });
    });
});
