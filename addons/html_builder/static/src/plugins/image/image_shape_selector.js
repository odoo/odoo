import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component, useRef } from "@odoo/owl";
import { getShapeURL } from "./image_helpers";

export class ImageShapeSelector extends Component {
    static template = "html_builder.ImageShapeSelector";
    static components = {
        ...defaultBuilderComponents,
    };
    static props = {};

    setup() {
        this.rootRef = useRef("root");
        this.shapeGroups = {
            basic: {
                label: "Basic",
                subgroups: {
                    geometrics: {
                        label: "Geometrics",
                        shapes: {
                            // todo: find it's proper place when implementing
                            // hovering an image without shape.
                            // "html_builder/geometric/geo_square": {
                            //     transform: false,
                            // },
                            "html_builder/geometric/geo_shuriken": {
                                selectLabel: "Shuriken",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric/geo_diamond": {
                                selectLabel: "Diamond",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric/geo_triangle": {
                                selectLabel: "Triangle",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_cornered_triangle": {
                                selectLabel: "Corner Triangle",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_pentagon": {
                                selectLabel: "Pentagon",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_hexagon": {
                                selectLabel: "Hexagon",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_heptagon": {
                                selectLabel: "Heptagon",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_star": {
                                selectLabel: "Star 1",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_star_8pin": {
                                selectLabel: "Star 2",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric/geo_star_16pin": {
                                selectLabel: "Star 3",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric/geo_slanted": {
                                selectLabel: "Slanted",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_emerald": {
                                selectLabel: "Emerald",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_tetris": {
                                selectLabel: "Tetris",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_kayak": {
                                selectLabel: "Kayak",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_tear": {
                                selectLabel: "Tear",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_gem": {
                                selectLabel: "Gem",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_sonar": {
                                selectLabel: "Sonar",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_door": {
                                selectLabel: "Door",
                                stretch: false,
                            },
                            "html_builder/geometric/geo_square_1": {
                                selectLabel: "Square 1",
                                animated: true,
                            },
                            "html_builder/geometric/geo_square_2": {
                                selectLabel: "Square 2",
                                animated: true,
                            },
                            "html_builder/geometric/geo_square_3": {
                                selectLabel: "Square 3",
                                animated: true,
                            },
                            "html_builder/geometric/geo_square_4": {
                                selectLabel: "Square 4",
                                animated: true,
                            },
                            "html_builder/geometric/geo_square_5": {
                                selectLabel: "Square 5",
                                animated: true,
                            },
                            "html_builder/geometric/geo_square_6": {
                                selectLabel: "Square 6",
                                animated: true,
                            },
                        },
                    },
                    geometrics_rounded: {
                        label: "Geometrics Rounded",
                        shapes: {
                            "html_builder/geometric_round/geo_round_circle": {
                                selectLabel: "Circle",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_square": {
                                selectLabel: "Square (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_diamond": {
                                selectLabel: "Diamond (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_shuriken": {
                                selectLabel: "Shuriken (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_triangle": {
                                selectLabel: "Triangle (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_pentagon": {
                                selectLabel: "Pentagon (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_hexagon": {
                                selectLabel: "Hexagon (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_heptagon": {
                                selectLabel: "Heptagon (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_star": {
                                selectLabel: "Star 1 (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_star_7pin": {
                                selectLabel: "Star 2 (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_star_8pin": {
                                selectLabel: "Star 3 (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_star_16pin": {
                                selectLabel: "Star 4 (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_emerald": {
                                selectLabel: "Emerald (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_lemon": {
                                selectLabel: "Lemon (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_tear": {
                                selectLabel: "Tear (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_pill": {
                                selectLabel: "Pill (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_gem": {
                                selectLabel: "Gem (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_cornered": {
                                selectLabel: "Cornered",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_door": {
                                selectLabel: "Door (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_sonar": {
                                selectLabel: "Sonar (R)",
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_clover": {
                                selectLabel: "Clover (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_bread": {
                                selectLabel: "Bread (R)",
                                transform: false,
                                stretch: false,
                            },
                            "html_builder/geometric_round/geo_round_square_1": {
                                selectLabel: "Square 1 (R)",
                                animated: true,
                            },
                            "html_builder/geometric_round/geo_round_square_2": {
                                selectLabel: "Square 2 (R)",
                                animated: true,
                            },
                            "html_builder/geometric_round/geo_round_blob_soft": {
                                selectLabel: "Blob Soft",
                                animated: true,
                            },
                            "html_builder/geometric_round/geo_round_blob_medium": {
                                selectLabel: "Blob Medium",
                                animated: true,
                            },
                            "html_builder/geometric_round/geo_round_blob_hard": {
                                selectLabel: "Blob Hard",
                                animated: true,
                            },
                        },
                    },
                    geometric_panels: {
                        label: "Geometrics Panels",
                        shapes: {
                            "html_builder/panel/panel_duo": {
                                selectLabel: "Duo",
                            },
                            "html_builder/panel/panel_duo_r": {
                                selectLabel: "Duo (R)",
                            },
                            "html_builder/panel/panel_duo_step": {
                                selectLabel: "Duo Step",
                            },
                            "html_builder/panel/panel_duo_step_pill": {
                                selectLabel: "Duo Step Pill",
                            },
                            "html_builder/panel/panel_trio_in_r": {
                                selectLabel: "Trio In (R)",
                            },
                            "html_builder/panel/panel_trio_out_r": {
                                selectLabel: "Trio Out (R)",
                            },
                            "html_builder/panel/panel_window": {
                                selectLabel: "Window",
                                transform: false,
                                stretch: false,
                            },
                        },
                    },
                    composites: {
                        label: "Composites",
                        shapes: {
                            "html_builder/composite/composite_double_pill": {
                                selectLabel: "Double Pill",
                            },
                            "html_builder/composite/composite_triple_pill": {
                                selectLabel: "Triple Pill",
                            },
                            "html_builder/composite/composite_half_circle": {
                                selectLabel: "Half Circle",
                            },
                            "html_builder/composite/composite_sonar": {
                                selectLabel: "Double Sonar",
                            },
                            "html_builder/composite/composite_cut_circle": {
                                selectLabel: "Cut Circle",
                            },
                        },
                    },
                },
            },
            decorative: {
                label: "Decorative",
                subgroups: {
                    brushed: {
                        label: "Brushed",
                        shapes: {
                            "html_builder/brushed/brush_1": {
                                selectLabel: "Brush 1",
                                stretch: false,
                            },
                            "html_builder/brushed/brush_2": {
                                selectLabel: "Brush 2",
                                stretch: false,
                            },
                            "html_builder/brushed/brush_3": {
                                selectLabel: "Brush 3",
                                stretch: false,
                            },
                            "html_builder/brushed/brush_4": {
                                selectLabel: "Brush 4",
                            },
                        },
                    },
                    composition: {
                        label: "Composition",
                        shapes: {
                            "html_builder/composition/composition_organic_line": {
                                selectLabel: "Organic Line",
                                transform: false,
                            },
                            "html_builder/composition/composition_oval_line": {
                                selectLabel: "Oval Line",
                                transform: false,
                            },
                            "html_builder/composition/composition_triangle_line": {
                                selectLabel: "Triangle Line",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_line_1": {
                                selectLabel: "Line 1",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_line_3": {
                                selectLabel: "Line 2",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_line_2": {
                                selectLabel: "Line 2",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_mixed_1": {
                                selectLabel: "Mixed 1",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_mixed_2": {
                                selectLabel: "Mixed 2",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_planet_1": {
                                selectLabel: "Planet 1",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_planet_2": {
                                selectLabel: "Planet 2",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_square_1": {
                                selectLabel: "Square Dot 1",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_square_2": {
                                selectLabel: "Square Dot 2",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_square_3": {
                                selectLabel: "Square Dot 3",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_square_4": {
                                selectLabel: "Square Dot 4",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/composition/composition_square_line": {
                                selectLabel: "Square Line",
                                animated: true,
                                transform: false,
                            },
                        },
                    },
                    patterns: {
                        label: "Patterns",
                        shapes: {
                            "html_builder/pattern/pattern_organic_cross": {
                                selectLabel: "Organic Cross",
                                transform: false,
                            },
                            "html_builder/pattern/pattern_organic_caps": {
                                selectLabel: "Organic Caps",
                                transform: false,
                            },
                            "html_builder/pattern/pattern_oval_zebra": {
                                selectLabel: "Oval Zebra",
                                transform: false,
                            },
                            "html_builder/pattern/pattern_wave_1": {
                                selectLabel: "Wave 1",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_line_star": {
                                selectLabel: "Star",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_line_sun": {
                                selectLabel: "Sun",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_wave_2": {
                                selectLabel: "Wave 2",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_wave_3": {
                                selectLabel: "Wave 3",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_point": {
                                selectLabel: "Point",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_organic_dot": {
                                selectLabel: "Organic Dot",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_labyrinth": {
                                selectLabel: "Labyrinth",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_circuit": {
                                selectLabel: "Circuit",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/pattern/pattern_wave_4": {
                                selectLabel: "Wave 4",
                                animated: true,
                                transform: false,
                            },
                        },
                    },
                    solids: {
                        label: "Solids",
                        shapes: {
                            "html_builder/solid/solid_blob_1": {
                                selectLabel: "Blob 1",
                                transform: false,
                            },
                            "html_builder/solid/solid_blob_2": {
                                selectLabel: "Blob 2",
                                transform: false,
                            },
                            "html_builder/solid/solid_blob_3": {
                                selectLabel: "Blob 3",
                                transform: false,
                            },
                            "html_builder/solid/solid_blob_4": {
                                selectLabel: "Blob 4",
                            },
                            "html_builder/solid/solid_blob_5": {
                                selectLabel: "Blob 5",
                                transform: false,
                            },
                            "html_builder/solid/solid_blob_shadow_1": {
                                selectLabel: "Blob Shadow 1",
                                transform: false,
                                anmated: true,
                            },
                            "html_builder/solid/solid_blob_shadow_2": {
                                selectLabel: "Blob Shadow 2",
                                transform: false,
                                anmated: true,
                            },
                            "html_builder/solid/solid_square_1": {
                                selectLabel: "Square 1",
                                transform: false,
                                anmated: true,
                            },
                            "html_builder/solid/solid_square_2": {
                                selectLabel: "Square 2",
                                transform: false,
                                anmated: true,
                            },
                            "html_builder/solid/solid_square_3": {
                                selectLabel: "Square 3",
                                transform: false,
                                anmated: true,
                            },
                        },
                    },
                    specials: {
                        label: "Specials",
                        shapes: {
                            "html_builder/special/special_speed": {
                                selectLabel: "Speed",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/special/special_rain": {
                                selectLabel: "Rain",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/special/special_snow": {
                                selectLabel: "Snow",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/special/special_layered": {
                                selectLabel: "Layered",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/special/special_filter": {
                                selectLabel: "Filter",
                                animated: true,
                                transform: false,
                            },
                            "html_builder/special/special_flag": {
                                selectLabel: "Flag",
                                animated: true,
                            },
                            "html_builder/special/special_organic": {
                                selectLabel: "Organic",
                                animated: true,
                            },
                        },
                    },
                },
            },
            devices: {
                label: "Devices",
                subgroups: {
                    devices: {
                        label: "Devices",
                        shapes: {
                            "html_builder/devices/iphone_front_portrait": {
                                selectLabel: "iPhone #1",
                                imgSize: "0.46:1",
                            },
                            "html_builder/devices/iphone_3d_portrait_01": {
                                selectLabel: "iPhone #2",
                                imgSize: "0.46:1",
                            },
                            "html_builder/devices/iphone_3d_portrait_02": {
                                selectLabel: "iPhone #3",
                                imgSize: "0.46:1",
                            },
                            "html_builder/devices/iphone_front_landscape": {
                                selectLabel: "iPhone #4",
                                imgSize: "2.17:1",
                            },
                            "html_builder/devices/iphone_3d_landscape_01": {
                                selectLabel: "iPhone #5",
                                imgSize: "2.17:1",
                            },
                            "html_builder/devices/iphone_3d_landscape_02": {
                                selectLabel: "iPhone #6",
                                imgSize: "2.17:1",
                            },
                            "html_builder/devices/galaxy_front_portrait": {
                                selectLabel: "Galaxy S #1",
                                imgSize: "0.45:1",
                            },
                            "html_builder/devices/galaxy_3d_portrait_01": {
                                selectLabel: "Galaxy S #2",
                                imgSize: "0.45:1",
                            },
                            "html_builder/devices/galaxy_3d_portrait_02": {
                                selectLabel: "Galaxy S #3",
                                imgSize: "0.45:1",
                            },
                            "html_builder/devices/galaxy_front_landscape": {
                                selectLabel: "Galaxy S #4",
                                imgSize: "2.22:1",
                            },
                            "html_builder/devices/galaxy_3d_landscape_01": {
                                selectLabel: "Galaxy S #5",
                                imgSize: "2.22:1",
                            },
                            "html_builder/devices/galaxy_3d_landscape_02": {
                                selectLabel: "Galaxy S #6",
                                imgSize: "2.22:1",
                            },
                            "html_builder/devices/galaxy_front_portrait_half": {
                                selectLabel: "Half Galaxy S",
                                imgSize: "0.45:1",
                            },
                            "html_builder/devices/ipad_front_portrait": {
                                selectLabel: "iPad #1",
                                imgSize: "0.75:1",
                            },
                            "html_builder/devices/ipad_3d_portrait_01": {
                                selectLabel: "iPad #2",
                                imgSize: "0.75:1",
                            },
                            "html_builder/devices/ipad_3d_portrait_02": {
                                selectLabel: "iPad #3",
                                imgSize: "0.75:1",
                            },
                            "html_builder/devices/ipad_front_landscape": {
                                selectLabel: "iPad #4",
                                imgSize: "4:3",
                            },
                            "html_builder/devices/ipad_3d_landscape_01": {
                                selectLabel: "iPad #5",
                                imgSize: "4:3",
                            },
                            "html_builder/devices/ipad_3d_landscape_02": {
                                selectLabel: "iPad #6",
                                imgSize: "4:3",
                            },
                            "html_builder/devices/imac_front": {
                                selectLabel: "iMac #1",
                                imgSize: "16:9",
                            },
                            "html_builder/devices/imac_3d_01": {
                                selectLabel: "iMac #2",
                                imgSize: "16:9",
                            },
                            "html_builder/devices/imac_3d_02": {
                                selectLabel: "iMac #3",
                                imgSize: "16:9",
                            },
                            "html_builder/devices/macbook_front": {
                                selectLabel: "MacBook #1",
                                imgSize: "1.6:1",
                            },
                            "html_builder/devices/macbook_3d_01": {
                                selectLabel: "MacBook #2",
                                imgSize: "1.6:1",
                            },
                            "html_builder/devices/macbook_3d_02": {
                                selectLabel: "MacBook #3",
                                imgSize: "1.6:1",
                            },
                            "html_builder/devices/browser_01": {
                                selectLabel: "Browser #1",
                            },
                            "html_builder/devices/browser_02": {
                                selectLabel: "Browser #2",
                            },
                            "html_builder/devices/browser_03": {
                                selectLabel: "Browser #3",
                            },
                        },
                    },
                },
            },
        };
    }
    getShapeUrl(shapePath) {
        return getShapeURL(shapePath);
    }
    closeComponent() {
        this.env.closeCustomizeComponent();
    }
    scrollToShapes(id) {
        this.rootRef.el
            ?.querySelector(`[data-shape-group-id="${id}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}
