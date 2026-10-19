/**
 * Meeting grid layouts offered in the "Adjust view" dialog. Every value except
 * {@link CALL_GRID_LAYOUT.DISCUSS} is persisted in user settings as `callLayout` and reused across
 * meetings (see {@link Settings.callLayout}).
 *
 * - `AUTO`: resolves dynamically to {@link CALL_GRID_LAYOUT.SPOTLIGHT} or
 *   {@link CALL_GRID_LAYOUT.TILED} from the screenshare state and participant count (see
 *   {@link Call.resolvedCallLayout}). The recommended default.
 * - `TILED`: an equally-sized tile per participant in a grid (the default layout of Google Meet).
 *   When `AUTO` resolves to it in fullscreen the grid is capped at 3 columns; picking `TILED`
 *   explicitly uses as many columns as fit.
 * - `SPOTLIGHT`: a single focused participant fills the view, the others are hidden.
 * - `SIDEBAR`: a single focused participant fills the view with the remaining participants stacked
 *   in a sidebar. Needs at least 2 participants, otherwise it falls back to one full-screen tile.
 * - `DISCUSS`: not a real grid layout — selecting it exits fullscreen back to the Discuss app and
 *   is never persisted.
 *
 * @typedef {"auto"|"tiled"|"spotlight"|"sidebar"|"discuss"} CallLayout
 */
export const CALL_GRID_LAYOUT = Object.freeze({
    AUTO: "auto",
    TILED: "tiled",
    SPOTLIGHT: "spotlight",
    SIDEBAR: "sidebar",
    DISCUSS: "discuss",
});
