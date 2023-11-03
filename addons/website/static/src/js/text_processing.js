/** @odoo-module **/

import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/utils/utils";

// SVG generator: contains all information needed to draw highlight SVGs
// according to text dimensions, highlight style,...
const _textHighlightFactory = {
    underline: targetEl => {
        return drawPath(targetEl, {mode: "line"});
    },
    freehand_1: targetEl => {
        const template = (w, h) => [`M 0,${h * 1.1} C ${w / 8},${h * 1.05} ${w / 4},${h} ${w},${h}`];
        return drawPath(targetEl, {mode: "free", template});
    },
    freehand_2: targetEl => {
        const template = (w, h) => [`M181.27 13.873c-.451-1.976-.993-3.421-1.072-4.9-.125-2.214-.61-4.856.384-6.539.756-1.287 3.636-2.055 5.443-1.852 3.455.395 7.001 1.231` +
        ` 10.14 2.676 1.728.802 3.174 3.06 3.817 4.98.237.712-1.953 2.824-3.399 3.4-2.766 1.095-5.748 1.75-8.706 2.179-2.394.339-4.879.068-6.584.068l-.023-.012ZM8.416 3.90` +
        `2c3.862.26 7.78.249 11.574.926 1.65.294 3.027 2.033 4.54 3.117-1.095 1.186-1.987 2.982-3.343 3.456a67.118 67.118 0 0 1-11.19 2.823c-3.253.53-6.494-.339-8.617-2.98` +
        `1C.364 9.978-.302 7.686.138 6.263c.361-1.152 2.54-2 4.077-2.44 1.287-.372 2.789.046 4.2.102v-.023Zm154.267 9.983c-4.291-.305-8.153-1.58-9.915-5.623-.745-1.694-.39` +
        `5-4.382.474-6.121 1.073-2.168 3.512-1.965 5.613-1.005 2.541 1.174 5.251 2.157 7.509 3.76 1.502 1.073 3.557 3.445 3.207 4.574-.519 1.694-2.857 2.913-4.562 4.133-.5` +
        `76.406-1.592.203-2.326.282ZM72.58 17.42c-2.733-1.807-5.307-3.004-7.137-4.913-.892-.925-.892-3.376-.361-4.776.407-1.05 2.304-2.112 3.546-2.135 3.602-.056 7.238.215` +
        ` 10.818.723 3.828.542 5.15 4.1 2.213 6.539-2.439 2.021-5.77 2.958-9.079 4.562Zm30.795-.802c-2.507-1.536-5.228-2.823-7.397-4.743-.925-.813-1.377-3.297-.813-4.359.6` +
        `78-1.265 2.677-2.507 4.11-2.518 3.016-.023 6.155.418 9.001 1.389 1.412.485 3.173 2.552 3.185 3.907 0 1.57-1.423 3.557-2.801 4.619-1.152.892-3.139.711-4.743 1.005-` +
        `.181.226-.35.463-.531.689l-.011.01Zm-59.704-1.457c-2.066-1.163-4.788-2.224-6.82-4.054-.915-.824-1.04-3.478-.407-4.765.486-.983 2.722-1.559 4.156-1.502 2.676.101 5` +
        `.398.542 7.95 1.332 1.457.452 3.523 1.75 3.681 2.891.18 1.31-1.13 3.309-2.383 4.201-1.411 1.005-3.466 1.118-6.188 1.886l.011.011Zm88.489-1.863c-2.643-1.48-5.567-2` +
        `.62-7.803-4.574-1.005-.88-1.31-3.692-.667-5.002.509-1.04 2.982-1.615 4.529-1.513 2.032.135 4.054 1.027 6.007 1.772 2.485.95 5.026 2.236 4.382 5.455-.644 3.15-3.49` +
        ` 2.947-5.963 3.004-.169.293-.327.575-.496.87l.011-.012Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 18, position: "bottom"});
    },
    freehand_3: targetEl => {
        const template = (w, h) => [`M189.705 18.285c-3.99.994-7.968 2.015-11.958 2.972-1.415.344-2.926 1.008-4.278.727-6.305-1.327-12.568-3.036-18.874-4.376-1.995-.42-4.2` +
        `46-.701-6.133-.038-5.867 2.067-11.54 2.386-17.374-.242-1.491-.676-3.56-.421-5.125.217-5.523 2.22-10.789 3.597-16.494.127-1.64-.995-4.675-.038-6.584 1.148-6.102 3.` +
        `789-12.01 4.414-18.198.434-.998-.638-2.681-.638-3.754-.115-6.852 3.355-13.404 2.858-20.043-1.008-1.5-.867-4.02-.6-5.608.307-7.528 4.35-14.842 5.702-22.07-.638-2.1` +
        `44-1.875-3.71-.37-5.394 1.046-4.622 3.89-9.565 6.327-15.367 4.286C6.338 20.989.505 13.067.022 5.949-.085 4.38.194 1.753.955 1.332 2.253.617 4.537.553 5.588 1.51 7` +
        `.55 3.27 9.18 5.77 10.52 8.296c2.82 5.269 4.15 5.766 8.504 2.156 1.555-1.288 2.992-2.768 4.396-4.286 4.022-4.311 7.143-4.465 11.26-.472 7.068 6.837 8.226 7.067 15` +
        `.979 1.314 3.721-2.755 7.206-2.653 10.627.128 4.987 4.056 9.791 4.49 14.853.191 2.702-2.296 5.78-2.296 8.45.115 4.29 3.89 8.45 3.33 12.719.166.847-.638 1.705-1.26` +
        `3 2.552-1.914 3.035-2.309 6.048-2.5 9.019.166 3.453 3.087 7.12 3.15 10.616.472 4.107-3.138 7.85-3.342 12.16-.306 3.668 2.59 7.83 1.964 11.594-.255 3.935-2.322 7.6` +
        `67-2.488 11.409.408.365.28.794.612 1.213.65 6.799.549 13.522 3.394 20.428.779 1.887-.715 3.914-1.034 5.899-1.148 3.313-.192 6.659-.358 9.941 0 1.993.23 4.354.905 ` +
        `5.737 2.436 1.308 1.429 2.113 4.235 2.123 6.442.022 3.023-2.424 3.431-4.472 3.597-1.887.153-3.796.038-5.695.038-.053-.216-.106-.446-.16-.663l.032-.025Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 24, position: "bottom"});
    },
    double: targetEl => {
        const template = (w, h) => [
            `M 0,${h * 0.9} h ${w}`,
            `M 0,${h * 1.1} h ${w}`,
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    wavy: targetEl => {
        const template = (w, h) => [
            `c ${w / 4},0 ${w / 4},-${h / 2} ${w / 2},-${h / 2}` +
            `c ${w / 4},0 ${w / 4},${h / 2} ${w / 2},${h / 2}`
        ];
        return drawPath(targetEl, {mode: "pattern", template});
    },
    circle_1: targetEl => {
        const template = (w, h) => [
            `M ${w / 2.88},${h / 1.1} C ${w / 1.1},${h / 1.05} ${w * 1.05},${h / 1.1} ${w * 1.023},${h / 2.32}` +
            `C ${w}, ${h / 14.6} ${w / 1.411},0 ${w / 2},0 S -2,${h / 14.6} -2,${h / 2.2}` +
            `S ${w / 4.24},${h} ${w / 1.36},${h * 1.04}`
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    circle_2: targetEl => {
        const template = (w, h) => [`M112.58 21.164h18.516c-.478-.176-1.722-.64-2.967-1.105.101-.401.214-.803.315-1.192 12.255 2.912 24.561 5.573 36.716 8.823 5.896 1.582 ` +
        `11.628 3.967 17.171 6.527 10.433 4.832 14.418 14.22 16.479 24.739.377 1.92.566 3.878.83 5.823 2.212 15.94-5.858 23.986-21.595 33.813-.993.615-2.288.79-3.181 1.494` +
        `-14.229 11.308-31.412 14.32-48.608 17.107-29.01 4.694-57.431 2.209-84.91-8.372-8.145-3.138-16.164-6.853-23.706-11.22C6.176 90.986 1.16 80.053.193 67.25c-1.798-23.` +
        `809 9.025-42.485 30.356-53.304C44.678 6.793 59.8 3.367 75.45 2.375 90.583 1.42 105.793.379 120.927.78c16.089.427 32.041 3.05 46.911 9.84 2.074.941 3.67 2.912 4.91` +
        `5 5.083-9.73-1.443-19.433-2.987-29.175-4.305-4.89-.665-9.842-1.067-14.77-1.33-23.82-1.28-47.376.514-70.391 7.003a133.771 133.771 0 0 0-22.639 8.648c-17.9 8.786-27` +
        `.616 26.935-25.567 46.364.666 6.263 3.507 11.133 9.05 14.308 26.862 15.401 55.748 21.965 86.645 19.819 15.561-1.08 31.01-2.787 45.767-8.284 11.099-4.142 21.658-9.` +
        `25 30.595-17.195 9.779-8.698 11.715-18.55 5.669-30.249-1.131-2.196-3.256-4.079-5.33-5.56-7.981-5.736-17.773-7.48-26.459-11.534-13.249-6.175-27.541-6.916-41.343-10` +
        `.167-.817-.188-1.571-.64-2.35-.966.037-.364.088-.728.125-1.092Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 120});
    },
    circle_3: targetEl => {
        const template = (w, h) => [`M78.653 89.204c-14.815 0-29.403-1.096-43.354-4.698-5.227-1.346-10.407-3.069-14.997-5.199-22.996-10.649-27.04-28.502-9.135-43.035 12.18` +
        `-9.866 26.813-18.04 43.355-24.242C88.515-.718 124.19-3.725 161.228 4.889c13.224 3.07 24.449 8.268 31.902 16.662 8.862 9.992 9.453 20.422 0 30.068-5.817 5.889-13.2` +
        `24 11.37-21.359 15.786-27.176 14.752-58.579 21.518-93.072 21.8h-.046Zm3.5-4.228c4.408-.282 11.725-.47 18.86-1.253 30.357-3.351 57.579-11.432 79.211-26.842 5.362-3` +
        `.82 10.134-8.832 12.27-13.875 2.545-5.982 5.817-13.311-6.226-17.352-.454-.156-.727-.563-1.045-.845-10.771-9.146-25.086-14.157-41.719-15.348-39.674-2.85-76.62 3.19` +
        `5-109.66 18.762-8.18 3.883-15.497 9.177-21.359 14.752-9.725 9.27-8.044 19.889 3.727 28.032 4.862 3.383 10.997 6.233 17.269 8.237 14.406 4.605 30.04 5.544 48.58 5.` +
        `763l.092-.03ZM130.37 3.573c-24.813-1.88-48.263 1.378-70.44 9.146 22.814-5.481 46.172-9.02 70.44-9.146Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 90});
    },
    over_underline: targetEl => {
        const template = (w, h) => [
            `M 0,0 h ${w}`,
            `M 0,${h} h ${w}`,
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    scribble_1: targetEl => {
        const template = (w, h) => [
            `M ${w / 2},${h * 0.9} c ${w / 16},0 ${w},1 ${w / 5},1 c 2,0 -${w / 10},-2 -${w / 2},-1` +
            `c -${w / 20},0 -${w / 5},2 -${w / 5},4 c -2,0 ${w / 10},-1 ${w / 2},${h / 16}` +
            `c ${w / 25},0 ${w / 10},0 ${w / 5},1 c 0,0 -${w / 10},1 -${w / 8},1` +
            `c -${w / 40},0 -${w / 16},0 -${w / 4},${h / 22}`
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    scribble_2: targetEl => {
        const template = (w, h) => [`M200 3.985c-.228-.332-3.773.541-.01-.006-.811-.037-6.705-1.442-9.978-1.706-1.473.194-2.907.534-4.351.818-1.398.27-2.937.985-4.144.756-` +
        `9.56-1.782-19.3-1.089-28.955-1.31C118.932 1.767 85.301.942 51.671.45c-13.732-.201-27.492.333-41.233.665C6.561 1.212 3.026 2.363.84 4.838.09 5.684-.262 7.126.223 7` +
        `.993c.313.554 2.518.79 3.839.728 2.47-.118 4.922-.548 8.096-.936-.96 1.227-1.568 1.865-1.986 2.558-1.368 2.302.029 4 3.203 4.083 24.716.666 49.424 1.4 74.15 2.01 ` +
        `21.087.52 42.145.34 63.146-1.414 4.495-.374 8.999-.644 14.425-1.026-3.117-1.629-4.723-3.521-8.39-3.535-17.999-.077-36.016-.07-54.005-.534-22.246-.576-44.464-1.58-` +
        `66.7-2.406-.276-.007-.551-.097-.817-.471 1.016 0 2.033-.021 3.04 0 21.961.506 43.913.998 65.864 1.539 25.249.624 50.47.367 75.642-1.144 5.892-.354 11.765-.93 17.6` +
        `19-1.54.788-.082 1.416-.99 2.651-1.92Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 17, position: "bottom"});
    },
    scribble_3: targetEl => {
        const template = (w, h) => [`M133.953 15.961c7.87.502 15.751.975 23.611 1.522 2.027.141 4.055.44 5.999.79 4.118.727 7.202 4.977 2.53 6.707.606.293 1.181.564 1.902.` +
        `908-8.477 2.069-17.267 2.65-26.203 2.818-19.023.361-38.056.603-57.068 1.088-13.807.355-27.572 1.06-41.369 1.545-3.23.113-6.532.096-9.73-.147-1.548-.118-3.492-.721` +
        `-4.234-1.42-.93-.88-1.484-2.199-.93-3.1.397-.655 2.812-1.263 4.41-1.33 6.397-.277 12.825-.333 19.243-.474 26.976-.592 53.942-1.156 80.919-1.804 3.742-.09 7.452-.5` +
        `92 11.173-.908 0-.174-.01-.35-.021-.524-2.717-.197-5.435-.53-8.163-.575-21.865-.383-43.741-1.009-65.607-.936-11.34.04-22.65 1.432-34 2.047-6.898.377-13.88.732-20.` +
        `779.569-7.044-.17-9.406-3.568-5.34-6.742 3.428-2.677 7.567-4.391 13.984-4.757 16.441-.93 32.798-2.26 49.219-3.27 14.162-.868 28.366-1.516 42.549-2.266.586-.034 1.` +
        `15-.147 1.641-.45-5.006 0-10.023-.012-15.029.01-1.077 0-2.154.186-3.24.192-18.793.18-37.596.355-56.389.507-10.672.085-21.343.13-32.014.153a65.89 65.89 0 0 1-6.167` +
        `-.277C1.787 5.555-.02 4.247 0 2.59 0 1.384.89.72 3.293.742c5.874.056 11.748.124 17.622.09C41.045.708 61.186.409 81.317.42c28.408.012 56.827.158 85.225.417 8.686.0` +
        `8 17.35.7 26.015 1.122 3.23.158 5.832.902 7.024 2.678 1.055 1.572.125 2.21-2.875 1.95a30.51 30.51 0 0 0-2.268-.107c-.397 0-.805.073-1.557.146.721.451 1.306.767 1.` +
        `777 1.128 2.926 2.238 1.641 4.013-3.272 4.369-13.483.958-26.966 1.91-40.459 2.767-3.334.214-6.752 0-10.118.085-2.31.062-4.609.299-6.909.462l.042.519.011.005Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 32, position: "bottom"});
    },
    scribble_4: targetEl => {
        const template = (w, h) => [`M96.414 17.157c1.34-2.173 2.462-4.075 3.649-5.944 2.117-3.335 5.528-4.302 9.372-2.694 3.962 1.651 4.89 3.575 3.908 8.073-.205.967-.388` +
        ` 1.934-.022 3.118 1.513-3.075 3.013-6.15 4.557-9.203 1.306-2.586 4.297-3.433 7.859-2.195 2.765.968 4.395 2.706 3.564 5.922-.529 2.054-1.005 4.118-.918 6.487.463-.` +
        `859 1.015-1.685 1.371-2.586 1.447-3.673 3.002-7.324 4.2-11.083.896-2.792 2.192-3.955 5.323-3.564 4.772.598 7.049 3.412 5.84 7.986-.626 2.38-1.22 4.77-1.144 7.486.` +
        `745-1.358 1.544-2.683 2.213-4.074a138.72 138.72 0 0 0 2.926-6.487c2.376-5.66 3.12-4.704 8.724-3.618 3.552.685 5.063 4.031 4.34 7.997-.616 3.423-1.166 6.856-1.749 ` +
        `10.29l.95.358c.993-2.151 2.062-4.27 2.958-6.454.594-1.456.886-3.042 1.403-4.53 2.43-6.911 2.43-6.813 9.566-5.542.928.163 2.656-.967 3.078-1.923.992-2.26 2.332-2.7` +
        `16 4.523-2.097 4.297 1.206 8.659 2.184 12.945 3.444 2.796.826 4.319 2.988 4.135 5.889-.173 2.684-.961 5.324-1.274 8.008-.734 6.4-1.361 12.799-2.019 19.21-.065.673` +
        `.043 1.38-.097 2.031-.551 2.477-.41 5.465-3.476 6.421-2.311.717-6.489-2.194-7.644-5.03-.206-.5-.357-1.01-.918-2.63-1.22 3.27-2.073 5.629-2.991 7.965-2.095 5.345-3` +
        `.66 5.954-8.874 3.705-.853-.37-2.354-.783-2.786-.359-3.163 3.075-5.971 1.217-8.853-.358-.378-.207-.81-.316-1.188-.457-5.851 7.65-12.502 4.596-15.061-3.944-1.543 3` +
        `.042-2.883 5.726-4.265 8.399-3.357 6.53-7.783 6.975-12.47 1.25-.485-.587-.992-1.152-1.511-1.75-5.647 6.715-12.848 2.293-15.19-6.063-1.253 2.25-2.257 3.88-3.099 5.` +
        `596-1.285 2.64-2.883 4.65-6.23 3.868-3.498-.826-6.532-4.085-6.65-7.225-.054-1.424 0-2.847-.475-4.433-1.393 2.879-2.71 5.802-4.19 8.637-3.228 6.204-6.067 6.824-11.` +
        `67 2.912-.962-.673-2.57-.988-3.704-.728-3.681.837-6.272-.619-8.626-3.248-.691-.783-2.084-1.771-2.807-1.543-4.243 1.347-6.91-.641-9.166-3.836-.378-.543-.8-1.053-1.` +
        `555-2.031-1.08 2.194-2.008 4.041-2.915 5.9-2.397 4.943-5.528 5.932-10.02 2.835-2.008-1.38-3.713-2.118-6.37-1.738-5.117.728-8.54-3.444-7.762-8.649.227-1.521.378-3.` +
        `064-.086-4.9-.853 1.369-1.793 2.684-2.548 4.107-2.775 5.259-5.301 5.856-10.074 2.206-.971-.75-1.803-1.674-2.86-2.673-.67.271-1.598 1.043-2.257.858-2.71-.771-5.625` +
        `-1.423-7.838-3.01-.842-.608-.378-3.683.108-5.465 2.008-7.41 4.232-14.755 6.413-22.11.572-1.945 1.166-3.901 1.943-5.77 1.89-4.52 5.02-5.454 9.145-2.89 1.144.706 2.` +
        `408 1.217 3.552 1.923 2.364 1.456 4.696 2.988 7.439 4.737C32.423 7.14 37.444 6.64 42.82 10.41c2.602-2.107 1.803-7.17 6.748-6.323 3.369.587 6.478 1.217 7.439 4.878` +
        ` 2.289-2.281 4.221-5.693 6.877-6.42 2.624-.718 5.992 1.26 9.599 2.216-.044.054.636-.565.96-1.348 1.048-2.499 2.883-3.4 5.42-2.825 2.775.62 5.474 1.304 6.284 4.76.` +
        `216.89 1.285 2.042 2.159 2.248 7.58 1.793 7.6 1.739 8.108 9.55v.012Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 61});
    },
    jagged: targetEl => {
        const template = (w, h) => [
            `q ${4 * w / 3} -${2 * w / 3} ${2 * w / 3} 0` +
            `c -${w / 3} ${w / 3} -${w / 3} ${w / 3} ${w / 3} 0`
        ];
        return drawPath(targetEl, {mode: "pattern", template});
    },
    cross: targetEl => {
        const template = (w, h) => [
            `M 0,0 L ${w},${h}`,
            `M 0,${h} L ${w},0`,
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    diagonal: targetEl => {
        const template = (w, h) => [`M 0,${h} L${w},0`];
        return drawPath(targetEl, {mode: "free", template});
    },
    strikethrough: targetEl => {
        return drawPath(targetEl, {mode: "line", position: "center"});
    },
    bold: targetEl => {
        const template = (w, h) => [`M136.604 41.568c5.373.513 10.746 1.047 16.12 1.479 14.437 1.13 29.327 4.047 42.858-4.294 4.92-3.04 2.346-13.56-2.687-13.395-.825.02-1.` +
        `635.062-2.46.082.858-3.677-.34-8.3-3.545-9.41 2.655.062 5.309.104 7.963.165 6.863.185 6.863-14.176 0-14.36A1958.994 1958.994 0 0 0 5.263 5.778C-.4 6.169-2.392 18.` +
        `455 3.84 19.893c9.727 2.24 19.454 4.335 29.214 6.307-1.085 1.09-1.764 2.671-2.023 4.356-.615.061-1.214.102-1.83.164-6.748.74-6.959 14.587 0 14.361l107.42-3.513h-.` +
        `016Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 46});
    },
    bold_1: targetEl => {
        const template = (w, h) => [`M190.276 34.01c5.618-.25 7.136-6.526 4.444-9.755.037-.25.055-.5.072-.749 7.046-.949 7.01-11.752-.523-11.553-.796.017-1.59.017-2.403.05` +
        `C196.78 9.573 195.931.8 189.264.983L13.784 5.678c-7.226.2-7.497 9.422-1.499 11.32-2.186 0-4.354 0-6.54-.017-7.696-.05-7.624 11.286 0 11.635 8.22.383 16.423.733 24` +
        `.643 1.016l-7.823.35c-7.624.349-7.678 11.985 0 11.635 55.915-2.53 111.813-5.077 167.729-7.607h-.018Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 42});
    },
    bold_2: targetEl => {
        const template = (w, h) => [`M193.221 20.193c.555 1.245.863 2.005 1.22 2.734 1.399 2.84 2.758 5.757 1.607 9.509-1.21 3.95-3.651 4.208-6.072 4.314-5.059.212-10.129.` +
        `152-15.178.592-15.873 1.367-31.737 3.585-47.619 4.238-19.921.82-39.862.638-59.802.486-13.938-.106-27.887-.88-41.825-1.428-4.018-.151-8.046-.47-12.064-.896-2.758-.` +
        `304-4.772-2.46-6.21-6.182-.645-1.656-1.756-2.993-2.798-4.177-2.768-3.13-5.06-6.38-3.899-12.502C.9 15.226.393 13.16.165 11.307c-.715-5.818.903-9.524 4.722-9.646 10` +
        `.218-.35 20.437-.38 30.655-.577C51.236.78 66.94-.04 82.635.264c14.652.273 29.296 1.655 43.948 2.643 19.822 1.336 39.643 2.02 59.455-.426.923-.121 1.835-.5 2.758-.` +
        `622 1.329-.183 2.688-.456 4.008-.274 3.829.501 7.073 5.666 7.192 11.21.09 4.466-1.418 6.213-6.775 7.428v-.03Z`];
        return drawPath(targetEl, {mode: "fill", template, SVGWidth: 200, SVGHeight: 43});
    },
};
// Returns the width of the DOMRect object.
export const getDOMRectWidth = el => el.getBoundingClientRect().width;

/**
 * Draws one or many SVG paths using templates of path shape commands.
 *
 * @param {HTMLElement} textEl
 * @param {String} options.mode Specifies how to draw the path:
 * - "pattern": repeat the template along the horizontal axis.
 * - "line": draw a simple line (we specify the width & position).
 * - "free": draw the path shape using the template only.
 * - "fill": used for irregular shapes that do not follow the "stroke" design.
 * @param {Function} options.template Returns a list of SVG path
 * commands adapted to the container's size.
 * @returns {String[]}
 */
function drawPath(textEl, options) {
    const {width, height} = textEl.getBoundingClientRect();
    options = {...options, width, height};
    const yStart = options.position === "center" ? height / 2 : height;

    switch (options.mode) {
        case "pattern": {
            let i = 0, d = [];
            const nbrChars = textEl.textContent.length;
            const w = width / nbrChars, h = height * 0.2;
            while (i < nbrChars) {
                d.push(options.template(w, h));
                i++;
            }
            return buildPath([`M 0,${yStart} ${d.join(" ")}`], options);
        }
        case "line": {
            return buildPath([`M 0,${yStart} h ${width}`], options);
        }
    }
    return buildPath(options.template(width, height), options);
}

/**
 * Used to build the SVG <path/>, it should mainly adapt it to take into
 * consideration some cases where the shape is a "filled path" instead
 * of a single line stroke.
 *
 * @param {String[]} templates
 * @param {Object} options
 * @returns {Element[]}
 */
function buildPath(templates, options) {
    return templates.map(d => {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("stroke-width", "var(--text-highlight-width)");
        path.setAttribute("stroke", "var(--text-highlight-color)");
        path.setAttribute("stroke-linecap", "round");
        if (options.mode === "fill") {
            let wScale = options.width / options.SVGWidth;
            let hScale = options.height / options.SVGHeight;
            const transforms = [];
            if (options.position === "bottom") {
                hScale *= 0.3;
                transforms.push(`translate(0 ${options.height * 0.8})`);
            }
            transforms.push(`scale(${wScale}, ${hScale})`);
            path.setAttribute("fill", "var(--text-highlight-color)");
            path.setAttribute("transform", transforms.join(" "));
        }
        path.setAttribute("d", d);
        return path;
    });
}

/**
 * Returns a new highlight SVG adapted to the text container.
 *
 * @param {HTMLElement} textEl
 * @param {String} highlightID
 */
export function drawTextHighlightSVG(textEl, highlightID) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("fill", "none");
    svg.classList.add(
        "o_text_highlight_svg",
        // Identifies DOM content that should not be merged by the editor, even
        // on identical parents.
        "o_content_no_merge",
        "position-absolute",
        "overflow-visible",
        "top-0",
        "start-0",
        "w-100",
        "h-100",
        "pe-none");
    _textHighlightFactory[highlightID](textEl).forEach(pathEl => {
        pathEl.classList.add(`o_text_highlight_path_${highlightID}`);
        svg.appendChild(pathEl);
    });
    return svg;
}

/**
 * Divides the content of a text container into multiple
 * `.o_text_highlight_item` units, and applies the highlight
 * on each unit.
 *
 * @param {HTMLElement} topTextEl
 * @param {String} highlightID
 */
export function applyTextHighlight(topTextEl, highlightID) {
    const lines = [];
    let lineIndex = 0;
    const nodeIsBR = node => node.nodeName === "BR";
    const isRTL = el => window.getComputedStyle(el).direction === "rtl";

    [...topTextEl.childNodes].forEach(child => {
        // We consider `<br/>` tags as full text lines to ease
        // excluding them when the highlight is applied on the DOM.
        if (nodeIsBR(child)) {
            lines[++lineIndex] = [child];
            return lineIndex++;
        }
        const textLines = splitNodeLines(child);

        // Special case: The text lines detection code in `splitNodeLines()`
        // (based on `getClientRects()`) can't handle a situation when a line
        // exactly ends with the current child node. We need to handle this
        // manually by checking if the current child node is the last one in
        // the line (taking into account the RTL direction).
        // TODO: Improve this.
        let lastNodeInLine = false;
        if (child.textContent && child.nextSibling?.textContent) {
            const range = document.createRange();
            const lastCurrentText = selectAllTextNodes(child).at(-1);
            range.setStart(lastCurrentText, lastCurrentText.length - 1);
            range.setEnd(lastCurrentText, lastCurrentText.length);
            // Get the "END" position of the last text node in current child.
            const currentEnd = range.getBoundingClientRect()[isRTL(topTextEl) ? "left" : "right"];
            const firstnextText = selectAllTextNodes(child.nextSibling)[0];
            range.setStart(firstnextText, 0);
            range.setEnd(firstnextText, 1);
            // Get the "START" position of the first text node in the next
            // sibling.
            const nextStart = range.getBoundingClientRect()[isRTL(topTextEl) ? "right" : "left"];
            // The next sibling starts before the end of the current node
            // => Line break detected.
            lastNodeInLine = nextStart + 1 < currentEnd;
        }

        // for each text line detected, we add the content as new
        // line and adjust the line index accordingly.
        textLines.map((node, i, {length}) => {
            if (!lines[lineIndex]) {
                lines[lineIndex] = [];
            }
            lines[lineIndex].push(node);
            if (i !== length - 1 || lastNodeInLine) {
                lineIndex++;
            }
        });
    });
    topTextEl.replaceChildren(...lines.map(textLine => {
        // First we add text content to be able to build svg paths
        // correctly (`<br/>` tags are excluded).
        return nodeIsBR(textLine[0]) ? textLine[0] :
            createHighlightContainer(textLine);
    }));
    // Build and set highlight SVGs.
    [...topTextEl.querySelectorAll(".o_text_highlight_item")].forEach(container => {
        container.append(drawTextHighlightSVG(container, highlightID));
    });
}

/**
 * Used to rollback the @see applyTextHighlight behaviour.
 *
 * @param {HTMLElement} topTextEl
 */
export function removeTextHighlight(topTextEl) {
    // Simply replace every `<span class="o_text_highlight_item">
    // textNode1 [textNode2,...]<svg .../></span>` by `textNode1
    // [textNode2,...]`.
    [...topTextEl.querySelectorAll(".o_text_highlight_item")].forEach(unit => {
        unit.after(...[...unit.childNodes].filter((node) => node.tagName !== "svg"));
        unit.remove();
    });
    // Prevents incorrect text lines detection on the next updates.
    let child = topTextEl.firstElementChild;
    while (child) {
        let next = child.nextElementSibling;
        // Merge identical elements.
        if (next && next === child.nextSibling && child.cloneNode().isEqualNode(next.cloneNode())) {
            child.replaceChildren(...child.childNodes, ...next.childNodes);
            next.remove();
        } else {
            child = next;
        }
    }
    topTextEl.normalize();
}

/**
 * Used to change or adjust the highlight effect when it's needed (E.g. on
 * window / text container "resize").
 *
 * @param {HTMLElement} textEl The top text highlight element.
 * @param {String} highlightID The new highlight to apply (or the old one
 * if we just want to adapt the effect).
 */
export function switchTextHighlight(textEl, highlightID) {
    const ownerDocument = textEl.ownerDocument;
    const sel = ownerDocument.getSelection();
    const restoreSelection = sel.rangeCount === 1 && textEl.contains(sel.anchorNode);
    let rangeCollapsed,
    cursorEndPosition = 0,
    rangeSize = 0;

    // Because of text highlight adaptations, the selection offset will
    // be lost, which will cause issues when typing and deleting text...
    // The goal here is to preserve the selection to restore it for the
    // new elements after the update when it's needed.
    if (restoreSelection) {
        const range = sel.getRangeAt(0);
        rangeSize = range.toString().length;
        rangeCollapsed = range.collapsed;
        // We need the position related to the `.o_text_highlight` element.
        const globalRange = range.cloneRange();
        globalRange.selectNodeContents(textEl);
        globalRange.setEnd(range.endContainer, range.endOffset);
        cursorEndPosition = globalRange.toString().length;
    }

    // Set the new text highlight effect.
    if (highlightID) {
        removeTextHighlight(textEl);
        applyTextHighlight(textEl, highlightID);
    }

    // Restore the old selection.
    if (restoreSelection && cursorEndPosition) {
        if (rangeCollapsed) {
            const selectionOffset = getOffsetNode(textEl, cursorEndPosition);
            OdooEditorLib.setSelection(...selectionOffset, ...selectionOffset);
        } else {
            OdooEditorLib.setSelection(
                ...getOffsetNode(textEl, cursorEndPosition - rangeSize),
                ...getOffsetNode(textEl, cursorEndPosition)
            );
        }
        ownerDocument.dispatchEvent(new Event("selectionchange"));
    }
}

/**
 * Used to wrap text nodes in a single "text highlight" unit.
 *
 * @param {Node[]} nodes
 * @returns {HTMLElement} The one line text element that should contain
 * the highlight SVG.
 */
function createHighlightContainer(nodes) {
    const highlightContainer = document.createElement("span");
    highlightContainer.className = "o_text_highlight_item";
    highlightContainer.append(...nodes);
    return highlightContainer;
}

/**
 * Used to get the current text highlight id from the top `.o_text_highlight`
 * container class.
 *
 * @param {HTMLElement} el
 * @returns {String}
 */
export function getCurrentTextHighlight(el) {
    const topTextEl = el.closest(".o_text_highlight");
    const match = topTextEl?.className.match(/o_text_highlight_(?<value>[\w]+)/);
    let highlight = "";
    if (match) {
        highlight = match.groups.value;
    }
    return highlight;
}

/**
 * Returns a list of detected lines in the content of a text node.
 *
 * @param {Node} node
 */
function splitNodeLines(node) {
    const isTextContainer = node.childNodes.length === 1
        && node.firstChild.nodeType === Node.TEXT_NODE;
    if (node.nodeType !== Node.TEXT_NODE && !isTextContainer) {
        return [node];
    }
    const text = node.textContent;
    const textNode = isTextContainer ? node.firstChild : node;
    const lines = [];
    const range = document.createRange();
    let i = -1;
    while (++i < text.length) {
        range.setStart(textNode, 0);
        range.setEnd(textNode, i + 1);
        const clientRects = range.getClientRects().length || 1;
        const lineIndex = clientRects - 1;
        const currentText = lines[lineIndex];
        lines[lineIndex] = (currentText || "") + text.charAt(i);
    }
    // Return the original node when no lines were detected.
    if (lines.length === 1) {
        return [node];
    }
    return lines.map(line => {
        if (isTextContainer) {
            const wrapper = node.cloneNode();
            wrapper.appendChild(document.createTextNode(line));
            return wrapper;
        }
        return document.createTextNode(line);
    });
}

/**
 * Get all text nodes inside a parent DOM element.
 *
 * @param {Node} topNode
 * @returns {Node[]} List of text "childNodes" or the element itself
 * (if it's a text node).
 */
export function selectAllTextNodes(topNode) {
    const textNodes = [];
    const selectTextNodes = (node) => {
        if (node.nodeType === Node.TEXT_NODE) {
            textNodes.push(node);
        } else {
            [...node.childNodes].forEach(child => selectTextNodes(child));
        }
    };
    selectTextNodes(topNode);
    return textNodes;
}

/**
 * Used to get the node of a text element in which a selection starts/ends.
 *
 * @param {HTMLElement} textEl The parent text element.
 * @param {Number} offset The selection offset in parent element.
 * @returns {[Node, Number]} The node found in the cursor position
 * and the new offset compared to that node.
 */
export function getOffsetNode(textEl, offset) {
    let index = 0,
    offsetNode;
    for (const node of selectAllTextNodes(textEl)) {
        const stepLength = node.textContent.length;
        if (index + stepLength < offset - 1) {
            index += stepLength;
        } else {
            offsetNode = node;
            break;
        }
    }
    return [offsetNode, offset - index];
}
