import io

import pytest

import qrcode
import qrcode.util
from qrcode.tests.consts import BLACK, RED, UNICODE_TEXT, WHITE

Image = pytest.importorskip("PIL.Image", reason="PIL is not installed")

if Image:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles import colormasks, moduledrawers


def test_render_pil():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image()
    img.save(io.BytesIO())
    assert isinstance(img.get_image(), Image.Image)


@pytest.mark.parametrize("back_color", ["TransParent", "red", (255, 195, 235)])
def test_render_pil_background(back_color):
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(back_color="TransParent")
    img.save(io.BytesIO())


def test_render_pil_with_rgb_color_tuples():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(back_color=(255, 195, 235), fill_color=(55, 95, 35))
    img.save(io.BytesIO())


def test_render_with_pattern():
    qr = qrcode.QRCode(mask_pattern=3)
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image()
    img.save(io.BytesIO())


def test_render_styled_Image():
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L)
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=StyledPilImage)
    img.save(io.BytesIO())


def test_render_styled_with_embeded_image():
    embeded_img = Image.new("RGB", (10, 10), color="red")
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_H)
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=StyledPilImage, embeded_image=embeded_img)
    img.save(io.BytesIO())


def test_render_styled_with_embeded_image_path(tmp_path):
    tmpfile = str(tmp_path / "test.png")
    embeded_img = Image.new("RGB", (10, 10), color="red")
    embeded_img.save(tmpfile)
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_H)
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=StyledPilImage, embeded_image_path=tmpfile)
    img.save(io.BytesIO())


@pytest.mark.parametrize(
    "drawer",
    [
        moduledrawers.CircleModuleDrawer,
        moduledrawers.GappedSquareModuleDrawer,
        moduledrawers.HorizontalBarsDrawer,
        moduledrawers.RoundedModuleDrawer,
        moduledrawers.SquareModuleDrawer,
        moduledrawers.VerticalBarsDrawer,
    ],
)
def test_render_styled_with_drawer(drawer):
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L)
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer(),
    )
    img.save(io.BytesIO())


@pytest.mark.parametrize(
    "mask",
    [
        colormasks.SolidFillColorMask(),
        colormasks.SolidFillColorMask(back_color=WHITE, front_color=RED),
        colormasks.SolidFillColorMask(back_color=(255, 0, 255, 255), front_color=RED),
        colormasks.RadialGradiantColorMask(
            back_color=WHITE, center_color=BLACK, edge_color=RED
        ),
        colormasks.SquareGradiantColorMask(
            back_color=WHITE, center_color=BLACK, edge_color=RED
        ),
        colormasks.HorizontalGradiantColorMask(
            back_color=WHITE, left_color=RED, right_color=BLACK
        ),
        colormasks.VerticalGradiantColorMask(
            back_color=WHITE, top_color=RED, bottom_color=BLACK
        ),
        colormasks.ImageColorMask(
            back_color=WHITE, color_mask_image=Image.new("RGB", (10, 10), color="red")
        ),
    ],
)
def test_render_styled_with_mask(mask):
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L)
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
    img.save(io.BytesIO())


def test_embedded_image_and_error_correction(tmp_path):
    "If an embedded image is specified, error correction must be the highest so the QR code is readable"
    tmpfile = str(tmp_path / "test.png")
    embedded_img = Image.new("RGB", (10, 10), color="red")
    embedded_img.save(tmpfile)

    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L)
    qr.add_data(UNICODE_TEXT)
    with pytest.raises(ValueError):
        qr.make_image(embeded_image_path=tmpfile)
    with pytest.raises(ValueError):
        qr.make_image(embeded_image=embedded_img)

    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_M)
    qr.add_data(UNICODE_TEXT)
    with pytest.raises(ValueError):
        qr.make_image(embeded_image_path=tmpfile)
    with pytest.raises(ValueError):
        qr.make_image(embeded_image=embedded_img)

    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_Q)
    qr.add_data(UNICODE_TEXT)
    with pytest.raises(ValueError):
        qr.make_image(embeded_image_path=tmpfile)
    with pytest.raises(ValueError):
        qr.make_image(embeded_image=embedded_img)

    # The only accepted correction level when an embedded image is provided
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_H)
    qr.add_data(UNICODE_TEXT)
    qr.make_image(embeded_image_path=tmpfile)
    qr.make_image(embeded_image=embedded_img)


def test_shortcut():
    qrcode.make("image")
