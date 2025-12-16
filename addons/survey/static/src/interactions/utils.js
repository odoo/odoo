// The given colors are the same as those used by D3
export const D3_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#aec7e8",
    "#ffbb78",
    "#2ca02c",
    "#98df8a",
    "#d62728",
    "#ff9896",
    "#9467bd",
    "#c5b0d5",
    "#8c564b",
    "#c49c94",
    "#e377c2",
    "#f7b6d2",
    "#7f7f7f",
    "#c7c7c7",
    "#bcbd22",
    "#dbdb8d",
    "#17becf",
    "#9edae5",
];

export function getStringColor(str, paletteSize = D3_COLORS.length) {
    const charsSum = Array.from(str).reduce((sum, char) => sum + char.charCodeAt(0), 0);
    return D3_COLORS[charsSum % paletteSize];
}
