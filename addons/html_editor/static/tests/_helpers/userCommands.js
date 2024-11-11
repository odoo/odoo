export function execCommand(editor, commandId, params) {
    const command = editor.shared.getCommand(commandId);
    if (!command) {
        throw new Error(`Unknown user command id: ${commandId}`);
    }
    return command.run(params);
}
