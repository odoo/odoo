export function sortDepositLines(lines) {
    if (!lines.some((line) => line.deposit_main_line_id)) {
        return lines;
    }
    const lineSet = new Set(lines);
    const sortedLines = [];
    const pushDepositLine = (line) => {
        if (lineSet.has(line.depositLine)) {
            sortedLines.push(line.depositLine);
        }
    };
    for (const line of lines) {
        if (lineSet.has(line.deposit_main_line_id)) {
            continue;
        }
        sortedLines.push(line);
        if (!line.combo_line_ids.length) {
            pushDepositLine(line);
        }
        const comboParent = line.combo_parent_id;
        if (comboParent?.combo_line_ids.at(-1) === line) {
            pushDepositLine(comboParent);
        }
    }
    return sortedLines;
}
