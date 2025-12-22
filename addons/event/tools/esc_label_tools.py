# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from base64 import b64decode
from typing import Literal, Optional
from PIL import Image
from odoo.tools import float_compare


class EscLabelCommand:
    """
    Class to encapsulate the ESC/Label commands used with the EPSON C4000e printer.

    The documentation can be found attached to task-4045816:
    - ESC/Label (CW-C4000 Series) Application Development Guide
    - ESC/Label Command List CW-C4000 Series
    - ESC/Label Command Reference Guide
    """
    _command = ""

    def _parse_color_string(self, color: str):
        return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))

    def _upload_pil_image(self, filename: str, image: Image.Image):
        png_buffer = io.BytesIO()
        image.save(png_buffer, format="PNG")
        png_data = png_buffer.getvalue()
        self._command += f"~DYR:{filename},A,P,{len(png_data)},0,{png_data.hex()}"
        return self

    def to_string(self):
        return self._command

    def wrap_command(self):
        """
        Wraps the command with ESC/Label 'begin' and 'end' markers.
        """
        self._command = f"^XA {self._command} ^XZ"
        return self

    def concat(self, other_command):
        """
        Concatenates two commands together.
        """
        self._command += other_command._command
        return self

    def delete_files(self, file_pattern: str):
        """
        Delete files matched by `file_pattern` from internal memory.
        """
        self._command += f"^IDR{file_pattern}^FS"
        return self

    def set_resolution(self, dots_per_inch: Literal[200, 300, 600]):
        """
        Set the resolution of the printer in dots per inch.

        Three separate commands are issued to set the format resolution,
        print resolution and replacement printer resolution (as recommened in the documentation).
        """
        self._command += f"^S(CLR,R,{dots_per_inch} ^S(CLR,P,{dots_per_inch} ^S(CLR,Z,{dots_per_inch}"
        return self

    def set_printable_area(self, width: int, length: int):
        """
        Sets the printable area.

        Note that `length` and `width` are in *dots*.
        For example at 600 DPI, 100mm is equal to 2362 dots. (100 * 600 / 25.4)
        """
        self._command += f"^S(CLS,P,{width} ^S(CLS,L,{length}"
        return self

    def set_label_gap(self, gap: int):
        """
        Sets the label gap (the distance in dots between each label).
        """
        self._command += f"^S(CLS,C,{gap}"
        return self

    def set_left_gap(self, gap: int):
        """
        Sets the left gap (the distance in dots from the left edge of the label to the printable area).
        """
        self._command += f"^S(CLS,G,{gap}"
        return self

    def set_printing_offset(self, left_offset: int, top_offset: int):
        """
        Offset the printing by the specfied numbers of dots, useful for alignment.

        The offsets can be positive or negative.
        """
        self._command += f"^S(CLE,M,{left_offset} ^S(CLE,T,{top_offset}"
        return self

    def set_utf8_encoding(self):
        """
        Call this to ensure that non-ASCII characters are printed correctly.
        """
        self._command += "^CI28"
        return self

    def set_print_quality(self, quality: Literal["D", "S", "N", "Q", "M"]):
        """
        Sets the print quality to one of the following:

        - D: Max Speed
        - S: Speed
        - N: Normal
        - Q: Quality
        - M: Max Quality
        """
        self._command += f"^CI28^S(CPC,Q,{quality}"
        return self

    def set_media_type(self, media_type: Literal["CP", "DL", "CL", "WB"]):
        """
        Sets the media type to one of the following:

        - CP: Continuous paper
        - DL: Die-cut label
        - CL: Continuous label
        - WB: Wristband
        """
        self._command += f"^S(CLM,F,{media_type}"
        return self

    def set_media_source(self, source: Literal["IR", "ER"]):
        """
        Sets the media source to one of the following:

        - IR: Internal roll
        - ER: External feed
        """
        self._command += f"^S(CLM,P,{source}"
        return self

    def set_media_shape(self, shape: Literal["RP", "FP"]):
        """
        Sets the media shape to one of the following:

        - RP: Roll paper
        - FP: Fanfold paper
        """
        self._command += f"^S(CLM,S,{shape}"
        return self

    def set_media_coating(self, coating: Literal["P1", "M1", "S1", "G1", "GS1", "PG1", "T1", "WB1"]):
        """
        Sets the media coating to one of the following:

        - P1: Plain Paper
        - M1: Matte Paper
        - S1: Synthetic
        - G1: Glossy Paper
        - GS1: Glossy Film
        - PG1: High Glossy Paper
        - T1: Texture Paper
        - WB1: Wristband
        """
        self._command += f"^S(CLM,T,{coating}"
        return self

    def set_edge_detection(self, detection_type: Literal["M", "W", "N"]):
        """
        Sets the edge detection method to one of the following:

        - M: Black mark detection
        - W: Gap detection
        - N: No detection
        """
        self._command += f"^S(CLM,D,{detection_type}"
        return self

    def upload_image(
        self,
        filename: str,
        image_field: str,
        size: Optional[tuple[int, int]] = None,
        crop_mode: Literal["contain", "cover"] = "contain",
        flip=False
    ):
        """
        Saves an image to the printer under the name `{filename}.PNG`.

        If `size` is specified, the image is resized first.
        The resizing behaviour is determined by `crop_mode`:
        - `"contain"`: Add transparent padding if needed
        - `"cover"`: Crop original image if needed

        If `flip` is `True`, the image is rotated 180° before uploading.
        """
        image_data = b64decode(image_field)
        image_buffer = io.BytesIO(image_data)
        image = Image.open(image_buffer)

        if flip:
            image = image.rotate(180)

        if size:
            target_width, target_height = size
            source_aspect = image.width / image.height
            target_aspect = target_width / target_height

            if float_compare(source_aspect, target_aspect, 2) == 0:
                image = image.resize(size=size)
            elif crop_mode == "cover":
                if target_aspect >= source_aspect:
                    crop_amount = int((image.height - (image.width / target_aspect)) / 2)
                else:
                    crop_amount = int((image.width - (image.height * target_aspect)) / 2)
                source_rect = (
                    (0, crop_amount, image.width, image.height - crop_amount)
                    if target_aspect >= source_aspect
                    else (crop_amount, 0, image.width - crop_amount, image.height)
                )
                image = image.resize(size=size, box=source_rect)
            elif crop_mode == "contain":
                container_image = Image.new("RGBA", size=size, color="#0000")
                if target_aspect >= source_aspect:
                    new_width = int(target_height * source_aspect)
                    padding_amount = int((target_width - new_width) / 2)
                    image = image.resize(size=(new_width, target_height))
                    container_image.paste(image, (padding_amount, 0))
                else:
                    new_height = int(target_width / source_aspect)
                    padding_amount = int((target_height - new_height) / 2)
                    image = image.resize(size=(target_width, new_height))
                    container_image.paste(image, (0, padding_amount))
                image = container_image

        return self._upload_pil_image(filename, image)

    def print_text(
        self,
        text: str,
        position: tuple[int, int],
        font_size: tuple[int, int],
        wrap_width: Optional[int] = None,
        max_lines: int = 1,
        align: Literal["L", "C", "R", "J"] = "L",
        rotation: Literal["N", "R", "I", "B"] = "N"
    ):
        """
        Prints text at the given `position` and `font_size`.
        If you specify a `wrap_width`, the text will print inside a container of
        that width, and you can align the text inside it using `align`:

        - L: Align left
        - C: Centred
        - R: Align right
        - J: Justify

        If the text exceeds `max_lines` in the container, the remaining text is truncated.

        The text `rotation` can be set as follows:

        - N: Normal
        - R: 90° rotation (clockwise)
        - I: 180° rotation
        - B: 270° rotation (clockwise)
        """
        command = f"^FO{position[0]},{position[1]}^A0{rotation},{font_size[0]},{font_size[1]}"
        if wrap_width:
            command += f"^FB{wrap_width},{max_lines},0,{align}"
        command += f"^FD{text}^FS"
        self._command += command
        return self

    def print_box(
        self,
        position: tuple[int, int],
        size: tuple[int, int],
        thickness: int = 1
    ):
        """
        Print a box, which has both an outline (foreground color) and a fill (background color).
        Specify the colors using `set_color`.
        """
        self._command += f"^FO{position[0]},{position[1]}^GB{size[0]},{size[1]},{thickness},B,0^FS"
        return self

    def print_image(self, filename: str, position: tuple[int, int]):
        """
        Print an image that was previously saved with `upload_image` at the specified `position`.
        """
        self._command += f"^FO{position[0]},{position[1]}^IMR:{filename}.PNG^FS"
        return self

    def set_color(
        self,
        color: tuple[int, int, int] | str,
        alpha: int = 255,
        bg_color: tuple[int, int, int] | str = (0, 0, 0),
        bg_alpha: int = 0,
    ):
        """
        Set the foreground and background color and transparency.
        The color only applies to the current field.
        """
        if isinstance(color, str):
            color = self._parse_color_string(color)
        if isinstance(bg_color, str):
            bg_color = self._parse_color_string(bg_color)

        self._command += f"^F(C{color[0]},{color[1]},{color[2]},{alpha},D,{bg_color[0]},{bg_color[1]},{bg_color[2]},{bg_alpha},D"
        return self

    def print_complete(self):
        """
        Signal that the current label is complete.
        """
        self._command += "^S(CUB,S,L"
        return self

    def save_canvas(self):
        """
        Save the current print as a template.
        """
        self._command += "^C(SN"
        return self

    def load_canvas(self):
        """
        Load the template that was saved earlier with `save_canvas`.
        """
        self._command += "^C(L"
        return self


def setup_printer(layout: dict):
    return (EscLabelCommand()
        .delete_files("*.*")  # Clean-up printer memory
        .set_resolution(600)  # 600 DPI
        .set_media_coating("M1")  # Matte paper
        .set_media_type("DL")  # Die-cut label
        .set_media_shape("FP")  # Fanfold paper
        .set_media_source("ER")  # External paper feed
        .set_edge_detection("W")  # Detect gap between labels
        .set_print_quality("N")  # Normal quality
        .set_utf8_encoding()
        .set_printable_area(layout["print_width"],
                            layout["print_height"] * 2 if layout["double_sided"] else layout["print_height"])
        .set_label_gap(layout["label_gap"])
        .set_left_gap(48)
        .set_printing_offset(layout["print_offset_left"], layout["print_offset_top"])
        .wrap_command()
    )


def print_centered_text(layout: dict, text: str, y_position: int, font_size: int, command: EscLabelCommand, flip=False):
    if flip:
        y_position = layout["print_height"] * 2 - y_position - font_size
    command.print_text(
        text,
        position=(layout["text_margin"], y_position),
        font_size=(font_size, font_size),
        wrap_width=layout["print_width"] - (layout["text_margin"] * 2),
        align="C",  # Center aligned
        rotation="I" if flip else "N"  # (I)nverted if printing flipped, otherwise (N)ormal
    )


def print_event_template(event: dict, layout: dict, flip=False):
    command = EscLabelCommand()

    if event["badge_image"]:
        command.print_image("BGFLIP" if flip else "BG", (0, layout["print_height"]) if flip else (0, 0))

    print_centered_text(
        layout,
        text=event["name"],
        y_position=layout["event_name_y_pos"],
        font_size=layout["event_name_font_size"],
        command=command,
        flip=flip
    )

    command.set_color(layout["secondary_text_color"], alpha=layout["secondary_text_alpha"])
    print_centered_text(
        layout,
        text=event["timeframe"],
        y_position=layout["date_y_pos"],
        font_size=layout["details_font_size"],
        command=command,
        flip=flip
    )

    if event["address"]:
        command.set_color(layout["secondary_text_color"], alpha=layout["secondary_text_alpha"])
        print_centered_text(
            layout,
            text=event["address"],
            y_position=layout["address_y_pos"],
            font_size=layout["details_font_size"],
            command=command,
            flip=flip
        )

    if event["logo"]:
        logo_x_pos = (layout["print_width"] - layout["logo_width"]) / 2
        logo_y_pos = layout["print_height"] * 2 - layout["logo_y_pos"] - layout["logo_height"] if flip else layout["logo_y_pos"]
        command.print_image("LOGOFLIP" if flip else "LOGO", (logo_x_pos, logo_y_pos))

    command.set_color(layout["secondary_text_color"], alpha=layout["secondary_text_alpha"])
    print_centered_text(
        layout,
        text=event["sponsor_text"],
        y_position=layout["custom_text_y_pos"],
        font_size=layout["details_font_size"],
        command=command,
        flip=flip
    )

    return command


def setup_event_template(event: dict, layout: dict):
    upload_images_command = EscLabelCommand()

    if event["badge_image"]:
        background_size = (layout["print_width"], layout["print_height"])
        upload_images_command.upload_image("BG", event["badge_image"], background_size, "cover")
        if layout["double_sided"]:
            upload_images_command.upload_image("BGFLIP", event["badge_image"], background_size, "cover", flip=True)
    if event["logo"]:
        upload_images_command.upload_image("LOGO", event["logo"], (layout["logo_width"], layout["logo_height"]),
                                            "contain")
        if layout["double_sided"]:
            upload_images_command.upload_image("LOGOFLIP", event["logo"],
                                                (layout["logo_width"], layout["logo_height"]), "contain", flip=True)

    template_command = print_event_template(event, layout)
    if layout["double_sided"]:
        template_command.concat(print_event_template(event, layout, flip=True))
    template_command.save_canvas().wrap_command()

    cleanup_command = EscLabelCommand().delete_files("*.*").wrap_command()

    return upload_images_command.concat(template_command).concat(cleanup_command)


def print_attendee_badge(attendee: dict, layout: dict, flip=False):
    command = EscLabelCommand()
    print_centered_text(
        layout,
        text=attendee["name"],
        y_position=layout["attendee_name_y_pos"],
        font_size=layout["attendee_name_font_size"],
        command=command,
        flip=flip
    )

    if attendee["company_name"]:
        print_centered_text(
            layout,
            text=attendee["company_name"],
            y_position=layout["company_y_pos"],
            font_size=layout["company_font_size"],
            command=command,
            flip=flip
        )

    if attendee["registration_answers"]:
        dots_between_answers = layout["details_font_size"] + 50
        for answer_index in range(0, len(attendee["registration_answers"])):
            command.set_color(layout["secondary_text_color"], alpha=layout["secondary_text_alpha"])
            print_centered_text(
                layout,
                text=attendee["registration_answers"][answer_index],
                y_position=layout["answers_y_pos"] + (dots_between_answers * answer_index),
                font_size=layout["details_font_size"],
                command=command,
                flip=flip
            )

    if attendee["ticket_name"]:
        ticket_bg_y_pos = layout["print_height"] if flip else layout["print_height"] - layout["ticket_bg_height"]
        (command
            .set_color(color=attendee["ticket_color"], bg_color=attendee["ticket_color"], bg_alpha=255)
            .print_box(position=(0, ticket_bg_y_pos), size=(layout["print_width"], layout["ticket_bg_height"]))
            )
        command.set_color(attendee["ticket_text_color"])
        print_centered_text(
            layout,
            text=attendee["ticket_name"],
            y_position=layout["ticket_text_y_pos"],
            font_size=layout["ticket_font_size"],
            command=command,
            flip=flip
        )

    return command


def print_event_attendees(event: dict, attendees: list[dict], layout: dict):
    event_command = setup_event_template(event, layout)

    for attendee in attendees:
        attendee_command = EscLabelCommand().load_canvas()
        attendee_command.concat(print_attendee_badge(attendee, layout))
        if layout["double_sided"]:
            attendee_command.concat(print_attendee_badge(attendee, layout, flip=True))
        event_command.concat(attendee_command.print_complete().wrap_command())

    return event_command


layout_96x82 = {
    "print_width": 2340,
    "print_height": 1965,
    "print_offset_left": -30,
    "print_offset_top": 50,
    "double_sided": True,
    "label_gap": 80,
    "text_margin": 160,
    "logo_width": 800,
    "logo_height": 300,
    "ticket_bg_height": 275,
    "event_name_font_size": 150,
    "details_font_size": 80,
    "attendee_name_font_size": 130,
    "company_font_size": 100,
    "ticket_font_size": 110,
    "event_name_y_pos": 350,
    "date_y_pos": 550,
    "address_y_pos": 670,
    "attendee_name_y_pos": 825,
    "company_y_pos": 980,
    "answers_y_pos": 1120,
    "logo_y_pos": 1200,
    "ticket_text_y_pos": 1780,
    "custom_text_y_pos": 1550,
    "secondary_text_color": "#374151",
    "secondary_text_alpha": 200
}


layout_96x134 = {
    "print_width": 2340,
    "print_height": 3225,
    "print_offset_left": -30,
    "print_offset_top": 36,
    "double_sided": True,
    "label_gap": 80,
    "text_margin": 160,
    "logo_width": 800,
    "logo_height": 300,
    "ticket_bg_height": 275,
    "event_name_font_size": 150,
    "details_font_size": 80,
    "attendee_name_font_size": 130,
    "company_font_size": 100,
    "ticket_font_size": 110,
    "event_name_y_pos": 450,
    "date_y_pos": 650,
    "address_y_pos": 770,
    "attendee_name_y_pos": 1025,
    "company_y_pos": 1200,
    "answers_y_pos": 1350,
    "logo_y_pos": 2380,
    "ticket_text_y_pos": 3040,
    "custom_text_y_pos": 2750,
    "secondary_text_color": "#374151",
    "secondary_text_alpha": 200
}
