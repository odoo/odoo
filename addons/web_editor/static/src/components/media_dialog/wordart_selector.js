/** @odoo-module */

import { Component, useRef, useState, onPatched } from "@odoo/owl";

export class WordartSelector extends Component {
    setup() {
        super.setup();

        this.svgRef = useRef("svg");
        this.state = useState({
            input: "",
            font: "Arial",
            fontSize: "4em",

            borderMulticolor: false,
            borderAnimation: false,
            strokeStep: "7",
            colors: ["#360745", "#D61C59", "#E7D84B", "#EFEAC5", "#1B8798"],

            curve: "M120,100 Q400,200 680,100",
            curveColor: "rgba(80, 80, 80, 0.5)",
            curveStrokeWidth: "0.5",

            useFill: true,
            borderPlain: false,
            fillGradient: {
                rotate: 15,
                stops: [{
                    offset: 5, //%
                    stopColor: "rgb(255, 204, 51)",
                }, {
                    offset: 95, //%
                    stopColor: "rgb(226, 51, 255)",
                }],
            },

            useShadow: true,
            shadowPosition: [0, 5], //x% y%
            useShifted: true,
            shiftedFills: [
                [0, 4.0, "#707070"],
                [0, 3.5, "#806060"],
                [0, 3.0, "#905050"],
                [0, 2.5, "#A04040"],
                [0, 2.0, "#B03030"],
                [0, 1.5, "#C02020"],
                [0, 1.0, "#D01010"],
                [0, 0.5, "#E00000"],
            ],
/*           
- spread
  - angle
  - clone spread
  - glow spread
  - count
  - palette steps (define as a single gradient ?)
- path
  - picklist + custom string
- shadow
  - color
  - intensity
- border
  - count
  - palette steps => === gradient definition
- fill gradient
  - gradient (or fill color)
*/
        });
        this.preset("3.11");

        onPatched(() => {
            while (this.props.selectedMedia[this.props.id].length) {
                this.props.selectedMedia[this.props.id].pop();
            }
            this.props.selectedMedia[this.props.id].push(this.svgRef.el.cloneNode(true));
        });

        this.placeholder = this.env._t("Some beautiful text");
        this.props.selectedMedia[this.props.id].push("wordart");
    }

    preset(name) {
        const presets = {
            "3.11": {
                borderMulticolor: false,
                borderAnimation: false,
    
                curve: "M120,300 680,200",
                curveColor: "transparent",
                curveStrokeWidth: "0",
    
                useFill: true,
                borderPlain: false,
                fillGradient: {
                    rotate: 15,
                    stops: [{
                        offset: 5, //%
                        stopColor: "rgb(255, 204, 51)",
                    }, {
                        offset: 95, //%
                        stopColor: "rgb(226, 51, 255)",
                    }],
                },
    
                useShadow: false,
                useShifted: true,
                shiftedFills: [
                    [0, 4.0, "#707070"],
                    [0, 3.5, "#806060"],
                    [0, 3.0, "#905050"],
                    [0, 2.5, "#A04040"],
                    [0, 2.0, "#B03030"],
                    [0, 1.5, "#C02020"],
                    [0, 1.0, "#D01010"],
                    [0, 0.5, "#E00000"],
                ],
            },
            "curvy": {
                borderMulticolor: false,
    
                curve: "M120,100 Q400,200 680,100",
                curveColor: "rgba(80, 80, 80, 0.5)",
                curveStrokeWidth: "0.5",
    
                useFill: true,
                borderPlain: false,
                fillGradient: {
                    rotate: 15,
                    stops: [{
                        offset: 5, //%
                        stopColor: "rgb(255, 204, 51)",
                    }, {
                        offset: 95, //%
                        stopColor: "rgb(226, 51, 255)",
                    }],
                },
    
                useShadow: true,
                shadowPosition: [0, 5], //x% y%
                useShifted: false,
            },
            "outline": {
                borderMulticolor: true,
                borderAnimation: true,
                strokeStep: "7",
                colors: ["#360745", "#D61C59", "#E7D84B", "#EFEAC5", "#1B8798"],
    
                curve: "",
    
                useFill: false,
                borderPlain: false,
    
                useShadow: false,
                useShifted: false,
            },
        };
        const target = presets[name];
        for (const key in target) {
            this.state[key] = target[key];
        }
    }

    /**
     * Utility methods, used by the MediaDialog component.
     */
    static createElements(selectedMedia) {
        // Already inside
        return selectedMedia;
    }
}
WordartSelector.mediaSpecificClasses = ["o_wordart"];
WordartSelector.mediaSpecificStyles = [];
WordartSelector.mediaExtraClasses = [
    'rounded-circle', 'rounded', 'img-thumbnail', 'shadow',
    /^text-\S+$/, /^bg-\S+$/, /^fa-\S+$/,
];
WordartSelector.tagNames = ['SVG'];
WordartSelector.template = 'web_editor.WordartSelector';
