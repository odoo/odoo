export const getDefaultTextColor = () => {
    const tempElement = document.createElement("div");
    document.body.appendChild(tempElement);
    const computedColor = window.getComputedStyle(tempElement).color;
    document.body.removeChild(tempElement);
    return computedColor;
};
