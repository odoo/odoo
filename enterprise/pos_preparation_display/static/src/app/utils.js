export const computeFontColor = (bgColor) => {
    if (!bgColor) {
        return "black";
    }

    var hexAr = bgColor.replace("#", "").match(/.{1,2}/g);
    var rgb = hexAr.map((col) => parseInt(col, 16));
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255 > 0.5 ? "black" : "white";
};
