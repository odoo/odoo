export function roundTimeSpent({ minutesSpent, minimum = 15, rounding = 15 }) {
    minutesSpent = Math.max(minimum, minutesSpent);
    if (rounding) {
        minutesSpent = Math.ceil(minutesSpent / rounding) * rounding;
    }
    return minutesSpent;
}
