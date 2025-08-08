export function useBackgroundOption(isActiveItem) {
    return { showColorFilter: () => isActiveItem("toggle_bg_image_id") };
}
