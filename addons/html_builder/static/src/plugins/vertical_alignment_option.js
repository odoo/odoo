import { BaseVerticalAlignmentOption } from "./base_vertical_alignment_option";

export class VerticalAlignmentOption extends BaseVerticalAlignmentOption {
    static selector =
        ".s_text_image, .s_image_text, .s_three_columns, .s_showcase, .s_numbers, .s_faq_collapse, .s_references, .s_accordion_image, .s_shape_image, .s_reviews_wall, .s_key_images, .s_cards_soft, .s_cards_grid";
    static applyTo = ".row";
    static name = "verticalAlignmentOption";
}
