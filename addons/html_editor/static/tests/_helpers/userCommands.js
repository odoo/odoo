export function execCommand(editor, commandId, params) {
    const command = editor.shared.userCommand.getCommand(commandId);
    if (!command) {
        throw new Error(`Unknown user command id: ${commandId}`);
    }
    if (
        command.isAvailable &&
        !command.isAvailable(editor.shared.selection.getSelectionData().editableSelection)
    ) {
        return;
    }
    command.run(params);
}
