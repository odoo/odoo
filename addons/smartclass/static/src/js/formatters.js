export function formatHumanReadable(num, precision = 2) {
    if (num === null || num === undefined || num === false) {
        return "NaN";
    }

    num = Number(num);
    if (isNaN(num)) {
        return "NaN";
    }

    const units = ["", "k", "M", "B", "T"];
    let unitIndex = 0;

    while (Math.abs(num) >= 1000 && unitIndex < units.length - 1) {
        num /= 1000;
        unitIndex++;
    }

    return num.toFixed(precision) + " " + units[unitIndex];
}
