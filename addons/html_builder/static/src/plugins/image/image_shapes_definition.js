import { _t } from "@web/core/l10n/translation";

export const imageShapeDefinitions = {
    basic: {
        label: _t("Basic"),
        subgroups: {
            geometrics: {
                label: _t("Geometrics"),
                shapes: {
                    // todo: find it's proper place when implementing
                    // hovering an image without shape.
                    "html_builder/geometric/geo_square": {
                        transform: false,
                        isTechnical: true,
                    },
                    "html_builder/geometric/geo_shuriken": {
                        selectLabel: _t("Shuriken"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_diamond": {
                        selectLabel: _t("Diamond"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_triangle": {
                        selectLabel: _t("Triangle"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_cornered_triangle": {
                        selectLabel: _t("Corner Triangle"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_pentagon": {
                        selectLabel: _t("Pentagon"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_hexagon": {
                        selectLabel: _t("Hexagon"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_heptagon": {
                        selectLabel: _t("Heptagon"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_star": {
                        selectLabel: _t("Star 1"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_star_8pin": {
                        selectLabel: _t("Star 2"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_star_16pin": {
                        selectLabel: _t("Star 3"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_slanted": {
                        selectLabel: _t("Slanted"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_emerald": {
                        selectLabel: _t("Emerald"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_tetris": {
                        selectLabel: _t("Tetris"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_kayak": {
                        selectLabel: _t("Kayak"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_tear": {
                        selectLabel: _t("Tear"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_gem": {
                        selectLabel: _t("Gem"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_sonar": {
                        selectLabel: _t("Sonar"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_door": {
                        selectLabel: _t("Door"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric/geo_square_1": {
                        selectLabel: _t("Square 1"),
                        animated: true,
                    },
                    "html_builder/geometric/geo_square_2": {
                        selectLabel: _t("Square 2"),
                        animated: true,
                    },
                    "html_builder/geometric/geo_square_3": {
                        selectLabel: _t("Square 3"),
                        animated: true,
                    },
                    "html_builder/geometric/geo_square_4": {
                        selectLabel: _t("Square 4"),
                        animated: true,
                    },
                    "html_builder/geometric/geo_square_5": {
                        selectLabel: _t("Square 5"),
                        animated: true,
                    },
                    "html_builder/geometric/geo_square_6": {
                        selectLabel: _t("Square 6"),
                        animated: true,
                    },
                },
            },
            geometrics_rounded: {
                label: _t("Geometrics Rounded"),
                shapes: {
                    "html_builder/geometric_round/geo_round_circle": {
                        selectLabel: _t("Circle"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_square": {
                        selectLabel: _t("Square (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_diamond": {
                        selectLabel: _t("Diamond (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_shuriken": {
                        selectLabel: _t("Shuriken (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_triangle": {
                        selectLabel: _t("Triangle (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_pentagon": {
                        selectLabel: _t("Pentagon (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_hexagon": {
                        selectLabel: _t("Hexagon (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_heptagon": {
                        selectLabel: _t("Heptagon (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_star": {
                        selectLabel: _t("Star 1 (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_star_7pin": {
                        selectLabel: _t("Star 2 (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_star_8pin": {
                        selectLabel: _t("Star 3 (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_star_16pin": {
                        selectLabel: _t("Star 4 (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_emerald": {
                        selectLabel: _t("Emerald (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_lemon": {
                        selectLabel: _t("Lemon (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_tear": {
                        selectLabel: _t("Tear (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_pill": {
                        selectLabel: _t("Pill (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_gem": {
                        selectLabel: _t("Gem (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_cornered": {
                        selectLabel: _t("Cornered"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_door": {
                        selectLabel: _t("Door (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_sonar": {
                        selectLabel: _t("Sonar (R)"),
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_clover": {
                        selectLabel: _t("Clover (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_bread": {
                        selectLabel: _t("Bread (R)"),
                        transform: false,
                        togglableRatio: true,
                    },
                    "html_builder/geometric_round/geo_round_square_1": {
                        selectLabel: _t("Square 1 (R)"),
                        animated: true,
                    },
                    "html_builder/geometric_round/geo_round_square_2": {
                        selectLabel: _t("Square 2 (R)"),
                        animated: true,
                    },
                    "html_builder/geometric_round/geo_round_blob_soft": {
                        selectLabel: _t("Blob Soft"),
                        animated: true,
                    },
                    "html_builder/geometric_round/geo_round_blob_medium": {
                        selectLabel: _t("Blob Medium"),
                        animated: true,
                    },
                    "html_builder/geometric_round/geo_round_blob_hard": {
                        selectLabel: _t("Blob Hard"),
                        animated: true,
                    },
                },
            },
            geometric_panels: {
                label: _t("Geometrics Panels"),
                shapes: {
                    "html_builder/panel/panel_duo": {
                        selectLabel: _t("Duo"),
                    },
                    "html_builder/panel/panel_duo_r": {
                        selectLabel: _t("Duo (R)"),
                    },
                    "html_builder/panel/panel_duo_step": {
                        selectLabel: _t("Duo Step"),
                    },
                    "html_builder/panel/panel_duo_step_pill": {
                        selectLabel: _t("Duo Step Pill"),
                    },
                    "html_builder/panel/panel_trio_in_r": {
                        selectLabel: _t("Trio In (R)"),
                    },
                    "html_builder/panel/panel_trio_out_r": {
                        selectLabel: _t("Trio Out (R)"),
                    },
                    "html_builder/panel/panel_window": {
                        selectLabel: _t("Window"),
                        transform: false,
                        togglableRatio: true,
                    },
                },
            },
            composites: {
                label: _t("Composites"),
                shapes: {
                    "html_builder/composite/composite_double_pill": {
                        selectLabel: _t("Double Pill"),
                    },
                    "html_builder/composite/composite_triple_pill": {
                        selectLabel: _t("Triple Pill"),
                    },
                    "html_builder/composite/composite_half_circle": {
                        selectLabel: _t("Half Circle"),
                    },
                    "html_builder/composite/composite_sonar": {
                        selectLabel: _t("Double Sonar"),
                    },
                    "html_builder/composite/composite_cut_circle": {
                        selectLabel: _t("Cut Circle"),
                    },
                },
            },
        },
    },
    decorative: {
        label: _t("Decorative"),
        subgroups: {
            brushed: {
                label: _t("Brushed"),
                shapes: {
                    "html_builder/brushed/brush_1": {
                        selectLabel: _t("Brush 1"),
                        togglableRatio: true,
                    },
                    "html_builder/brushed/brush_2": {
                        selectLabel: _t("Brush 2"),
                        togglableRatio: true,
                    },
                    "html_builder/brushed/brush_3": {
                        selectLabel: _t("Brush 3"),
                        togglableRatio: true,
                    },
                    "html_builder/brushed/brush_4": {
                        selectLabel: _t("Brush 4"),
                    },
                },
            },
            composition: {
                label: _t("Composition"),
                shapes: {
                    "html_builder/composition/composition_organic_line": {
                        selectLabel: _t("Organic Line"),
                        transform: false,
                    },
                    "html_builder/composition/composition_oval_line": {
                        selectLabel: _t("Oval Line"),
                        transform: false,
                    },
                    "html_builder/composition/composition_triangle_line": {
                        selectLabel: _t("Triangle Line"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_line_1": {
                        selectLabel: _t("Line 1"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_line_3": {
                        selectLabel: _t("Line 2"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_line_2": {
                        selectLabel: _t("Line 2"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_mixed_1": {
                        selectLabel: _t("Mixed 1"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_mixed_2": {
                        selectLabel: _t("Mixed 2"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_planet_1": {
                        selectLabel: _t("Planet 1"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_planet_2": {
                        selectLabel: _t("Planet 2"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_square_1": {
                        selectLabel: _t("Square Dot 1"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_square_2": {
                        selectLabel: _t("Square Dot 2"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_square_3": {
                        selectLabel: _t("Square Dot 3"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_square_4": {
                        selectLabel: _t("Square Dot 4"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/composition/composition_square_line": {
                        selectLabel: _t("Square Line"),
                        animated: true,
                        transform: false,
                    },
                },
            },
            patterns: {
                label: _t("Patterns"),
                shapes: {
                    "html_builder/pattern/pattern_organic_cross": {
                        selectLabel: _t("Organic Cross"),
                        transform: false,
                    },
                    "html_builder/pattern/pattern_organic_caps": {
                        selectLabel: _t("Organic Caps"),
                        transform: false,
                    },
                    "html_builder/pattern/pattern_oval_zebra": {
                        selectLabel: _t("Oval Zebra"),
                        transform: false,
                    },
                    "html_builder/pattern/pattern_wave_1": {
                        selectLabel: _t("Wave 1"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_line_star": {
                        selectLabel: _t("Star"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_line_sun": {
                        selectLabel: _t("Sun"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_wave_2": {
                        selectLabel: _t("Wave 2"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_wave_3": {
                        selectLabel: _t("Wave 3"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_point": {
                        selectLabel: _t("Point"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_organic_dot": {
                        selectLabel: _t("Organic Dot"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_labyrinth": {
                        selectLabel: _t("Labyrinth"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_circuit": {
                        selectLabel: _t("Circuit"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/pattern/pattern_wave_4": {
                        selectLabel: _t("Wave 4"),
                        animated: true,
                        transform: false,
                    },
                },
            },
            solids: {
                label: _t("Solids"),
                shapes: {
                    "html_builder/solid/solid_blob_1": {
                        selectLabel: _t("Blob 1"),
                        transform: false,
                    },
                    "html_builder/solid/solid_blob_2": {
                        selectLabel: _t("Blob 2"),
                        transform: false,
                    },
                    "html_builder/solid/solid_blob_3": {
                        selectLabel: _t("Blob 3"),
                        transform: false,
                    },
                    "html_builder/solid/solid_blob_4": {
                        selectLabel: _t("Blob 4"),
                    },
                    "html_builder/solid/solid_blob_5": {
                        selectLabel: _t("Blob 5"),
                        transform: false,
                    },
                    "html_builder/solid/solid_blob_shadow_1": {
                        selectLabel: _t("Blob Shadow 1"),
                        transform: false,
                        animated: true,
                    },
                    "html_builder/solid/solid_blob_shadow_2": {
                        selectLabel: _t("Blob Shadow 2"),
                        transform: false,
                        animated: true,
                    },
                    "html_builder/solid/solid_square_1": {
                        selectLabel: _t("Square 1"),
                        transform: false,
                        animated: true,
                    },
                    "html_builder/solid/solid_square_2": {
                        selectLabel: _t("Square 2"),
                        transform: false,
                        animated: true,
                    },
                    "html_builder/solid/solid_square_3": {
                        selectLabel: _t("Square 3"),
                        transform: false,
                        animated: true,
                    },
                },
            },
            specials: {
                label: _t("Specials"),
                shapes: {
                    "html_builder/special/special_speed": {
                        selectLabel: _t("Speed"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/special/special_rain": {
                        selectLabel: _t("Rain"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/special/special_snow": {
                        selectLabel: _t("Snow"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/special/special_layered": {
                        selectLabel: _t("Layered"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/special/special_filter": {
                        selectLabel: _t("Filter"),
                        animated: true,
                        transform: false,
                    },
                    "html_builder/special/special_flag": {
                        selectLabel: _t("Flag"),
                        animated: true,
                    },
                    "html_builder/special/special_organic": {
                        selectLabel: _t("Organic"),
                        animated: true,
                    },
                },
            },
        },
    },
    devices: {
        label: _t("Devices"),
        subgroups: {
            devices: {
                label: _t("Devices"),
                shapes: {
                    "html_builder/devices/iphone_front_portrait": {
                        selectLabel: _t("iPhone #1"),
                        imgSize: "0.46:1",
                        transform: false,
                    },
                    "html_builder/devices/iphone_3d_portrait_01": {
                        selectLabel: _t("iPhone #2"),
                        imgSize: "0.46:1",
                        transform: false,
                    },
                    "html_builder/devices/iphone_3d_portrait_02": {
                        selectLabel: _t("iPhone #3"),
                        imgSize: "0.46:1",
                        transform: false,
                    },
                    "html_builder/devices/iphone_front_landscape": {
                        selectLabel: _t("iPhone #4"),
                        imgSize: "2.17:1",
                        transform: false,
                    },
                    "html_builder/devices/iphone_3d_landscape_01": {
                        selectLabel: _t("iPhone #5"),
                        imgSize: "2.17:1",
                        transform: false,
                    },
                    "html_builder/devices/iphone_3d_landscape_02": {
                        selectLabel: _t("iPhone #6"),
                        imgSize: "2.17:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_front_portrait": {
                        selectLabel: _t("Galaxy S #1"),
                        imgSize: "0.45:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_3d_portrait_01": {
                        selectLabel: _t("Galaxy S #2"),
                        imgSize: "0.45:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_3d_portrait_02": {
                        selectLabel: _t("Galaxy S #3"),
                        imgSize: "0.45:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_front_landscape": {
                        selectLabel: _t("Galaxy S #4"),
                        imgSize: "2.22:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_3d_landscape_01": {
                        selectLabel: _t("Galaxy S #5"),
                        imgSize: "2.22:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_3d_landscape_02": {
                        selectLabel: _t("Galaxy S #6"),
                        imgSize: "2.22:1",
                        transform: false,
                    },
                    "html_builder/devices/galaxy_front_portrait_half": {
                        selectLabel: _t("Half Galaxy S"),
                        imgSize: "0.45:1",
                        transform: false,
                    },
                    "html_builder/devices/ipad_front_portrait": {
                        selectLabel: _t("iPad #1"),
                        imgSize: "0.75:1",
                        transform: false,
                    },
                    "html_builder/devices/ipad_3d_portrait_01": {
                        selectLabel: _t("iPad #2"),
                        imgSize: "0.75:1",
                        transform: false,
                    },
                    "html_builder/devices/ipad_3d_portrait_02": {
                        selectLabel: _t("iPad #3"),
                        imgSize: "0.75:1",
                        transform: false,
                    },
                    "html_builder/devices/ipad_front_landscape": {
                        selectLabel: _t("iPad #4"),
                        imgSize: "4:3",
                        transform: false,
                    },
                    "html_builder/devices/ipad_3d_landscape_01": {
                        selectLabel: _t("iPad #5"),
                        imgSize: "4:3",
                        transform: false,
                    },
                    "html_builder/devices/ipad_3d_landscape_02": {
                        selectLabel: _t("iPad #6"),
                        imgSize: "4:3",
                        transform: false,
                    },
                    "html_builder/devices/imac_front": {
                        selectLabel: _t("iMac #1"),
                        imgSize: "16:9",
                        transform: false,
                    },
                    "html_builder/devices/imac_3d_01": {
                        selectLabel: _t("iMac #2"),
                        imgSize: "16:9",
                        transform: false,
                    },
                    "html_builder/devices/imac_3d_02": {
                        selectLabel: _t("iMac #3"),
                        imgSize: "16:9",
                        transform: false,
                    },
                    "html_builder/devices/macbook_front": {
                        selectLabel: _t("MacBook #1"),
                        imgSize: "1.6:1",
                        transform: false,
                    },
                    "html_builder/devices/macbook_3d_01": {
                        selectLabel: _t("MacBook #2"),
                        imgSize: "1.6:1",
                        transform: false,
                    },
                    "html_builder/devices/macbook_3d_02": {
                        selectLabel: _t("MacBook #3"),
                        imgSize: "1.6:1",
                        transform: false,
                    },
                    "html_builder/devices/browser_01": {
                        selectLabel: _t("Browser #1"),
                        transform: false,
                    },
                    "html_builder/devices/browser_02": {
                        selectLabel: _t("Browser #2"),
                        transform: false,
                    },
                    "html_builder/devices/browser_03": {
                        selectLabel: _t("Browser #3"),
                        transform: false,
                    },
                },
            },
        },
    },
};
