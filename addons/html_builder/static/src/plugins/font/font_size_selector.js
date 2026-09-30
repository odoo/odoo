import { FontSizeSelector } from "@html_editor/main/font/font_size_selector";

export class BuilderFontSizeSelector extends FontSizeSelector {
    static template = "html_builder.FontSizeSelector";
    setup() {
        super.setup();
        this.fontSizeTags = {
            "display-1-font-size": "Display 1",
            "display-2-font-size": "Display 2",
            "display-3-font-size": "Display 3",
            "display-4-font-size": "Display 4",
            "h1-font-size": "Heading 1",
            "h2-font-size": "Heading 2",
            "h3-font-size": "Heading 3",
            "h4-font-size": "Heading 4",
            "h5-font-size": "Heading 5",
            "h6-font-size": "Normal",
            "font-size-base": "Normal",
            "small-font-size": "Small",
        };
    }
}
