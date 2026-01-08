import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
const CONSOLE_COLOR = "#F5B427";

export const getStrNotes = (note) => {
    if (!note) {
        return "";
    }
    if (Array.isArray(note)) {
        return note.map((n) => (typeof n === "string" ? n : n.text)).join(", ");
    }
    if (typeof note === "string") {
        try {
            const parsed = JSON.parse(note);
            if (Array.isArray(parsed)) {
                return parsed.map((n) => (typeof n === "string" ? n : n.text)).join(", ");
            }
            return note;
        } catch (error) {
            logPosMessage(
                "OrderChange",
                "getStrNotes",
                "Error while parsing note, not valid JSON",
                CONSOLE_COLOR,
                [error]
            );
            return note;
        }
    }
    return "";
};
